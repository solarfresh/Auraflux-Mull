"""OpenSearch Client Singleton and Health Check Utilities.

This module manages the connection pool lifecycle for OpenSearch within the Django runtime.
"""

import logging
from typing import Optional
from django.conf import settings
from opensearchpy import OpenSearch, OpenSearchException

logger = logging.getLogger(__name__)

# Module-level variable to hold the singleton instance
_opensearch_client_instance: Optional[OpenSearch] = None


def get_opensearch_client() -> OpenSearch:
    """Returns a singleton instance of the OpenSearch client.

    Uses thread-safe connection pooling to reuse HTTP connections across Django requests.
    """
    global _opensearch_client_instance

    if _opensearch_client_instance is None:
        config = getattr(settings, "OPENSEARCH", {})

        hosts = config.get("HOSTS", ["http://localhost:9200"])
        auth = config.get("AUTH", ("admin", "admin"))
        use_ssl = config.get("USE_SSL", False)
        verify_certs = config.get("VERIFY_CERTS", False)
        max_connections = config.get("MAX_CONNECTIONS", 20)
        timeout = config.get("TIMEOUT", 30)
        max_retries = config.get("MAX_RETRIES", 3)

        try:
            _opensearch_client_instance = OpenSearch(
                hosts=hosts,
                http_auth=auth,
                use_ssl=use_ssl,
                verify_certs=verify_certs,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
                maxsize=max_connections,  # Reuses TCP connections via urllib3 pool
                timeout=timeout,
                max_retries=max_retries,
                retry_on_timeout=True,
            )
            logger.info("Initialized OpenSearch client singleton successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            raise e

    return _opensearch_client_instance


def check_opensearch_health() -> bool:
    """Performs an active health check ping against the OpenSearch cluster."""
    try:
        client = get_opensearch_client()
        is_healthy = client.ping()
        if not is_healthy:
            logger.warning("OpenSearch cluster ping failed.")
        return is_healthy
    except OpenSearchException as e:
        logger.error(f"OpenSearch health check encountered an error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during OpenSearch health check: {e}")
        return False


def close_opensearch_client() -> None:
    """Closes all connections in the OpenSearch connection pool."""
    global _opensearch_client_instance
    if _opensearch_client_instance is not None:
        try:
            _opensearch_client_instance.close()
            logger.info("Closed OpenSearch connection pool.")
        except Exception as e:
            logger.error(f"Error while closing OpenSearch client: {e}")
        finally:
            _opensearch_client_instance = None
