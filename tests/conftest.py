from __future__ import annotations

import shutil

import pytest


@pytest.fixture(scope="session")
def spark_available() -> bool:
    return shutil.which("java") is not None


@pytest.fixture(scope="session")
def spark(spark_available: bool):
    if not spark_available:
        pytest.skip("A Java runtime is required for PySpark integration tests")
    from pyspark.sql import SparkSession

    session = SparkSession.builder.master("local[2]").appName("StreamPulseTests").getOrCreate()
    yield session
    session.stop()