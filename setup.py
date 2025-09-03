from setuptools import setup, find_packages

setup(
    name="weev",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        # List your main dependencies here
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "sqlalchemy",
        "pydantic",
        "httpx",
        "websockets",
        "langchain",
        "langchain-community",
        "sentence-transformers",
        "chromadb",
        "numpy",
        "pytest",
        "pytest-asyncio",
    ],
    python_requires=">=3.8",
)
