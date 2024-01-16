import argparse
import asyncio
from typing import Any, Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential

from prepdocslib.blobmanager import BlobManager
from prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    OpenAIEmbeddings,
    OpenAIEmbeddingService,
)
from prepdocslib.filestrategy import DocumentAction, FileStrategyTest
from prepdocslib.listfilestrategy import (
    ADLSGen2ListFileStrategy,
    ListFileStrategy,
    LocalListFileStrategy,
)
from prepdocslib.pdfparser import DocumentAnalysisPdfParser, LocalPdfParser, PdfParser
from prepdocslib.strategy import SearchInfo, Strategy
from prepdocslib.textsplitter import TextSplitter

import html
from abc import ABC
from typing import IO, AsyncGenerator, Union

from azure.ai.formrecognizer import DocumentTable
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from pypdf import PdfReader


from .strategy import USER_AGENT

class Page:
    """
    A single page from a pdf

    Attributes:
        page_num (int): Page number
        offset (int): If the text of the entire PDF was concatenated into a single string, the index of the first character on the page. For example, if page 1 had the text "hello" and page 2 had the text "world", the offset of page 2 is 5 ("hellow")
        text (str): The text of the page
    """

    def __init__(self, page_num: int, offset: int, text: str):
        self.page_num = page_num
        self.offset = offset
        self.text = text


class DocumentAnalysisPdfParserURL(PdfParser):
    """
    Concrete parser backed by Azure AI Document Intelligence that can parse PDFS into pages
    To learn more, please visit https://learn.microsoft.com/azure/ai-services/document-intelligence/overview
    """

    def __init__(
        self,
        endpoint: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        model_id="prebuilt-layout",
        verbose: bool = False,
    ):
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.verbose = verbose

        self.formurl = "https://sa4rade.blob.core.windows.net/public/zhanlan/纺织面料_13388707.pdf"

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        if self.verbose:
            print(f"Extracting text from '{content.name}' using Azure Document Intelligence")

        async with DocumentAnalysisClient(
            endpoint=self.endpoint, credential=self.credential, headers={"x-ms-useragent": USER_AGENT}
        ) as form_recognizer_client:
            # poller = await form_recognizer_client.begin_analyze_document(model_id=self.model_id, document=content)
            poller = await form_recognizer_client.begin_analyze_document_from_url(model_id=self.model_id, document_url=self.formurl) 
            form_recognizer_results = await poller.result()

            offset = 0
            for page_num, page in enumerate(form_recognizer_results.pages):
                tables_on_page = [
                    table
                    for table in (form_recognizer_results.tables or [])
                    if table.bounding_regions and table.bounding_regions[0].page_number == page_num + 1
                ]

                # mark all positions of the table spans in the page
                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                table_chars = [-1] * page_length
                for table_id, table in enumerate(tables_on_page):
                    for span in table.spans:
                        # replace all table spans with "table_id" in table_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                table_chars[idx] = table_id

                # build page text by replacing characters in table spans with table html
                page_text = ""
                added_tables = set()
                for idx, table_id in enumerate(table_chars):
                    if table_id == -1:
                        page_text += form_recognizer_results.content[page_offset + idx]
                    elif table_id not in added_tables:
                        page_text += DocumentAnalysisPdfParser.table_to_html(tables_on_page[table_id])
                        added_tables.add(table_id)

                yield Page(page_num=page_num, offset=offset, text=page_text)
                offset += len(page_text)

    @classmethod
    def table_to_html(cls, table: DocumentTable):
        table_html = "<table>"
        rows = [
            sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index)
            for i in range(table.row_count)
        ]
        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
                cell_spans = ""
                if cell.column_span is not None and cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span is not None and cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html += "</tr>"
        table_html += "</table>"
        return table_html

def is_key_empty(key):
    return key is None or len(key.strip()) == 0


def setup_file_strategy(credential: AsyncTokenCredential, args: Any) -> FileStrategyTest:

    list_file_strategy: ListFileStrategy
    list_file_strategy = LocalListFileStrategy(path_pattern=args.files, verbose=args.verbose)

    formrecognizer_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
            credential if is_key_empty(args.formrecognizerkey) else AzureKeyCredential(args.formrecognizerkey)
        )
    pdf_parser = DocumentAnalysisPdfParserURL(
        endpoint=f"https://{args.formrecognizerservice}.cognitiveservices.azure.com/",
        credential=formrecognizer_creds,
        verbose=args.verbose,
    )

    return FileStrategyTest(
            list_file_strategy=list_file_strategy,
            # blob_manager=blob_manager,
            pdf_parser=pdf_parser,
            text_splitter=TextSplitter(),
            # document_action=document_action,
            # embeddings=embeddings,
            # search_analyzer_name=args.searchanalyzername,
            # use_acls=args.useacls,
            # category=args.category,
        )



async def main(strategy: Strategy, credential: AsyncTokenCredential, args: Any):
    search_creds: Union[AsyncTokenCredential, AzureKeyCredential] = (
        credential if is_key_empty(args.searchkey) else AzureKeyCredential(args.searchkey)
    )
    search_info = SearchInfo(
        endpoint=f"https://{args.searchservice}.search.windows.net/",
        credential=search_creds,
        index_name=args.index,
        verbose=args.verbose,
    )

    if not args.remove and not args.removeall:
        await strategy.setup(search_info)

    await strategy.run(search_info)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare documents by extracting content from PDFs, splitting content into sections, uploading to blob storage, and indexing in a search index.",
        epilog="Example: prepdocs.py '..\data\*' --storageaccount myaccount --container mycontainer --searchservice mysearch --index myindex -v",
    )
    parser.add_argument("files", nargs="?", help="Files to be processed")
    parser.add_argument(
        "--datalakestorageaccount", required=False, help="Optional. Azure Data Lake Storage Gen2 Account name"
    )
    parser.add_argument(
        "--datalakefilesystem",
        required=False,
        default="gptkbcontainer",
        help="Optional. Azure Data Lake Storage Gen2 filesystem name",
    )
    parser.add_argument(
        "--datalakepath",
        required=False,
        help="Optional. Azure Data Lake Storage Gen2 filesystem path containing files to index. If omitted, index the entire filesystem",
    )
    parser.add_argument(
        "--datalakekey", required=False, help="Optional. Use this key when authenticating to Azure Data Lake Gen2"
    )
    parser.add_argument(
        "--useacls", action="store_true", help="Store ACLs from Azure Data Lake Gen2 Filesystem in the search index"
    )
    parser.add_argument(
        "--category", help="Value for the category field in the search index for all sections indexed in this run"
    )
    parser.add_argument(
        "--skipblobs", action="store_true", help="Skip uploading individual pages to Azure Blob Storage"
    )
    parser.add_argument("--storageaccount", help="Azure Blob Storage account name")
    parser.add_argument("--container", help="Azure Blob Storage container name")
    parser.add_argument(
        "--storagekey",
        required=False,
        help="Optional. Use this Azure Blob Storage account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--tenantid", required=False, help="Optional. Use this to define the Azure directory where to authenticate)"
    )
    parser.add_argument(
        "--searchservice",
        help="Name of the Azure AI Search service where content should be indexed (must exist already)",
    )
    parser.add_argument(
        "--index",
        help="Name of the Azure AI Search index where content should be indexed (will be created if it doesn't exist)",
    )
    parser.add_argument(
        "--searchkey",
        required=False,
        help="Optional. Use this Azure AI Search account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument(
        "--searchanalyzername",
        required=False,
        default="en.microsoft",
        help="Optional. Name of the Azure AI Search analyzer to use for the content field in the index",
    )
    parser.add_argument("--openaihost", help="Host of the API used to compute embeddings ('azure' or 'openai')")
    parser.add_argument("--openaiservice", help="Name of the Azure OpenAI service used to compute embeddings")
    parser.add_argument(
        "--openaideployment",
        help="Name of the Azure OpenAI model deployment for an embedding model ('text-embedding-ada-002' recommended)",
    )
    parser.add_argument(
        "--openaimodelname", help="Name of the Azure OpenAI embedding model ('text-embedding-ada-002' recommended)"
    )
    parser.add_argument(
        "--novectors",
        action="store_true",
        help="Don't compute embeddings for the sections (e.g. don't call the OpenAI embeddings API during indexing)",
    )
    parser.add_argument(
        "--disablebatchvectors", action="store_true", help="Don't compute embeddings in batch for the sections"
    )
    parser.add_argument(
        "--openaikey",
        required=False,
        help="Optional. Use this Azure OpenAI account key instead of the current user identity to login (use az login to set current user for Azure). This is required only when using non-Azure endpoints.",
    )
    parser.add_argument("--openaiorg", required=False, help="This is required only when using non-Azure endpoints.")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove references to this document from blob storage and the search index",
    )
    parser.add_argument(
        "--removeall",
        action="store_true",
        help="Remove all blobs from blob storage and documents from the search index",
    )
    parser.add_argument(
        "--localpdfparser",
        action="store_true",
        help="Use PyPdf local PDF parser (supports only digital PDFs) instead of Azure Document Intelligence service to extract text, tables and layout from the documents",
    )
    parser.add_argument(
        "--formrecognizerservice",
        required=False,
        help="Optional. Name of the Azure Document Intelligence service which will be used to extract text, tables and layout from the documents (must exist already)",
    )
    parser.add_argument(
        "--formrecognizerkey",
        required=False,
        help="Optional. Use this Azure Document Intelligence account key instead of the current user identity to login (use az login to set current user for Azure)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = (
        AzureDeveloperCliCredential()
        if args.tenantid is None
        else AzureDeveloperCliCredential(tenant_id=args.tenantid, process_timeout=60)
    )

    file_strategy = setup_file_strategy(azd_credential, args)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(file_strategy, azd_credential, args))
    loop.close()
