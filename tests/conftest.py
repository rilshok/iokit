"""Fixtures shared by the test suite."""

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import uuid4

import pytest


@dataclass(frozen=True)
class S3Service:
    """A running S3 service and the credentials to reach it with."""

    endpoint_url: str
    access_key: str = "testing"
    secret_access_key: str = "testing"  # noqa: S105
    region_name: str = "us-east-1"

    def bucket(self) -> str:
        """Create an empty bucket on the service and return its name."""
        import boto3  # noqa: PLC0415  # only the tests reaching an S3 need it installed

        name = f"iokit-{uuid4().hex}"
        boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
        ).create_bucket(Bucket=name)
        return name


@pytest.fixture(scope="session", name="s3_service")
def s3_service_fixture() -> Iterator[S3Service]:
    """Serve a stand-in S3 on a local port, so that nothing here touches the network."""
    pytest.importorskip("boto3", reason="boto3 is needed to reach an S3")
    moto_server = pytest.importorskip("moto.server", reason="moto is needed to serve a fake S3")
    werkzeug_serving = pytest.importorskip("werkzeug.serving")

    server = werkzeug_serving.make_server("127.0.0.1", 0, moto_server.create_backend_app("s3"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield S3Service(endpoint_url=f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown()
        thread.join(timeout=10)
