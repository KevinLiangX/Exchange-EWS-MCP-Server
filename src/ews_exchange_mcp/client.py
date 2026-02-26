from exchangelib import Credentials, Configuration, Account, DELEGATE
import urllib3
import logging
import ssl

from .config import EWS_ENDPOINT, EWS_USERNAME, EWS_PASSWORD, NODE_TLS_REJECT_UNAUTHORIZED

logger = logging.getLogger("ews_mcp")

# Handle SSL verification bypass securely and dynamically
if NODE_TLS_REJECT_UNAUTHORIZED == "0":
    import requests
    from exchangelib.protocol import BaseProtocol
    
    # 彻底关闭证书校验并降低 SSL 严格程度以兼容旧版无修补的 Exchange Server
    class TLSAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            # 允许传统的弱加密套件以防 UNEXPECTED_EOF_WHILE_READING
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
            kwargs['ssl_context'] = ctx
            return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

    BaseProtocol.HTTP_ADAPTER_CLS = TLSAdapter
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("SSL Certificate Verification is DISABLED with Legacy Ciphers Enabled.")

def _create_account() -> Account:
    logger.info("Initializing EWS Exchange Service connecting to %s...", EWS_ENDPOINT)
    credentials = Credentials(username=EWS_USERNAME, password=EWS_PASSWORD)
    # Depending on the server, auth_type might be default NTLM or Basic. exchangelib autodiscovers it usually
    # or you can enforce NTLM. We'll stick to auto resolving if service_endpoint is set manually.
    config = Configuration(
        service_endpoint=EWS_ENDPOINT,
        credentials=credentials,
        auth_type='NTLM'
    )
    
    account = Account(
        primary_smtp_address=EWS_USERNAME,
        config=config,
        autodiscover=False,
        access_type=DELEGATE
    )
    return account

_account_instance = None

def get_ews_client() -> Account:
    """Returns a singleton of the EWS Account."""
    global _account_instance
    if _account_instance is None:
         _account_instance = _create_account()
    return _account_instance
