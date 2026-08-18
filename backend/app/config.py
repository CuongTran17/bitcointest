from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bitcoin_rpc_host: str = "127.0.0.1"
    bitcoin_rpc_port: int = 18443
    bitcoin_rpc_user: str = "bitcoinuser"
    bitcoin_rpc_password: str = "bitcoinpass"
    database_url: str = "sqlite:///./local_bitcoin_bank.db"
    cors_origins: list[str] = ["http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
