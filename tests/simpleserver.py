"""A simple HTTP server for testing CITE runner's GitHub action.

This is a server that purposedly does not fully implement OGC API Features. The
intention is to use this to test ogc-cite-runner's ability to be called as a GitHub action.
"""

import argparse
import dataclasses
import json
import logging
from typing import (
    Protocol,
    Type,
)
from http.client import HTTPMessage
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)
import urllib.parse

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class HttpRequest:
    headers: dict[str, str]
    url: urllib.parse.ParseResult

    @property
    def base_url(self) -> str:
        return "{scheme}://{host}/".format(
            scheme=self.url.scheme,
            host=self.url.netloc,
        )

    @classmethod
    def from_raw_request(
        cls: Type["HttpRequest"], raw_headers: HTTPMessage, raw_path: str
    ) -> "HttpRequest":
        parsed_headers = parse_headers(raw_headers)
        parsed_url = parse_url(parsed_headers.get("Host", ""), raw_path)
        return HttpRequest(
            headers=parsed_headers,
            url=parsed_url,
        )


def parse_headers(raw_headers: HTTPMessage) -> dict[str, str | list[str]]:
    result = {}
    for name in raw_headers.keys():
        value = raw_headers.get_all(name)
        if len(value) == 1:
            result[name] = value[0]
        else:
            result[name] = value
    return result


def parse_url(host: str, path: str) -> urllib.parse.ParseResult:
    scheme = "http"
    full_url = f"{scheme}://{host}{path}"
    return urllib.parse.urlparse(full_url)


@dataclasses.dataclass
class OgcApiLink:
    href: str
    rel: str
    title: str
    type: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class OgcApiLandingPage:
    title: str
    description: str
    links: list[OgcApiLink]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "links": [link.to_dict() for link in self.links],
        }


@dataclasses.dataclass
class Collection:
    id: str
    title: str
    description: str
    keywords: str
    extent: str
    item_type: str
    crs: str
    storage_crs: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class DataCatalog:
    title: str
    description: str
    collections: dict[str, Collection]

    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description
        self.collections = {
            "test-collection-1": Collection(
                id="test-collection-1",
                title="Test Collection 1",
                description="This is a test collection",
                keywords="test, collection, 1",
                extent="100, 100",
                item_type="test-item-type",
                crs="EPSG:4326",
                storage_crs="EPSG:4326",
            ),
        }

    def list_collections(self) -> list[Collection]:
        return list(self.collections.values())

    def get_collection(self, collection_id: str) -> Collection | None:
        return self.collections.get(collection_id)


class OgcApiRequestHandler(Protocol):
    def __call__(
        self,
        catalog: DataCatalog,
        request: HttpRequest,
        encoding: str = "utf-8",
        **path_parameters: dict[str:str],
    ) -> tuple[int, dict[str, str], bytes]: ...


class OGCCiteRunnerApiFeaturesHandler(BaseHTTPRequestHandler):
    catalog: DataCatalog

    def do_GET(self):
        encoding = "utf-8"
        request = HttpRequest.from_raw_request(self.headers, self.path)
        logger.debug(f"{request=}")
        handler_info = select_handler(request)
        logger.debug(f"{handler_info=}")
        if handler_info is not None:
            try:
                handler, path_parameters = handler_info
            except TypeError:
                handler = handler_info
                path_parameters = {}
            status, headers, body = handler(
                self.catalog, request, encoding=encoding, **path_parameters
            )
        else:
            status, headers, body = (
                404,
                {
                    "Content-type": f"application/json; charset={encoding}",
                },
                json.dumps({"error": "Not found"}).encode(encoding),
            )
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


def select_handler(
    request: HttpRequest,
) -> (
    OgcApiRequestHandler
    | OgcApiRequestHandler
    | tuple[OgcApiRequestHandler, dict[str, str]]
    | None
):
    match request.url.path.split("/")[1:]:
        case [""]:
            return get_landing_page
        case ["collections"]:
            return list_collections
        case ["collections", collection_id]:
            return get_collection, {"collection_id": collection_id}
        case _:
            return None


def get_landing_page(
    catalog: DataCatalog, request: HttpRequest, encoding: str = "utf-8"
) -> tuple[int, dict[str, str], bytes]:
    json_media_type = "application/json"
    openapi_v3_media_type = "application/vnd.oai.openapi+json;version=3.0"
    landing_page = OgcApiLandingPage(
        title=catalog.title,
        description=catalog.description,
        links=[
            OgcApiLink(
                href=f"{request.base_url}",
                rel="self",
                title="This document",
                type=json_media_type,
            ),
            OgcApiLink(
                href=f"{request.base_url}openapi",
                rel="service-desc",
                title="OpenAPI definition",
                type=openapi_v3_media_type,
            ),
            OgcApiLink(
                href=f"{request.base_url}conformance",
                rel="conformance",
                title="Conformance",
                type=json_media_type,
            ),
            OgcApiLink(
                href=f"{request.base_url}collections",
                rel="data",
                title="Collections",
                type=json_media_type,
            ),
        ],
    )
    return (
        200,
        {
            "Content-type": f"{json_media_type}; charset={encoding}",
        },
        json.dumps(landing_page.to_dict()).encode(encoding),
    )


def list_collections(
    catalog: DataCatalog, request: HttpRequest, encoding: str = "utf-8"
) -> tuple[int, dict[str, str], bytes]:
    serialized_collections = []
    for collection in catalog.list_collections():
        serialized_collections.append(collection.to_dict())

    return (
        200,
        {
            "Content-type": f"application/json; charset={encoding}",
        },
        json.dumps(
            {"collections": serialized_collections, "links": []},
        ).encode(encoding),
    )


def get_collection(
    catalog: DataCatalog,
    request: HttpRequest,
    encoding: str = "utf-8",
    *,
    collection_id: str,
) -> tuple[int, dict[str, str], bytes]:
    return (
        200,
        {
            "Content-type": f"application/json; charset={encoding}",
        },
        json.dumps(
            {
                "collection_id_was": collection_id,
            },
        ).encode(encoding),
    )


def main(bind_address: str, port: int):
    OGCCiteRunnerApiFeaturesHandler.catalog = DataCatalog(
        title="Simple server",
        description="A basic OGC API Features server, built for testing ogc-cite-runner as a GitHub Action.",
    )
    logger.info(f"Launching {OGCCiteRunnerApiFeaturesHandler.catalog.title!r}...")
    logger.info(f"Listening on http://{bind_address}:{port}")
    httpd = HTTPServer((bind_address, port), OGCCiteRunnerApiFeaturesHandler)
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-b", "--bind-address", default="localhost", help="Address to bind to"
    )
    parser.add_argument("-p", "--bind-port", default="8000", help="Port to bind to")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    main(bind_address=args.bind_address, port=int(args.bind_port))
