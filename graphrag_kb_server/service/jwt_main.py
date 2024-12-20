import asyncio
from graphrag_kb_server.model.jwt_token import JWTTokenData, JWTToken
from graphrag_kb_server.service.jwt_service import generate_token

TENNANT_JSON = "tennant.json"


def main(name: str, email: str):
    token = asyncio.run(generate_token(JWTTokenData(name=name, email=email), False))
    if isinstance(token, JWTToken):
        print(token.token)
    else:
        print("Could not generate token.")


if __name__ == "__main__":
    main("Onepoint Consulting", "gil.fernandes@onepointltd.com")
