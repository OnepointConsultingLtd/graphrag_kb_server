import asyncio
import argparse
import yaml

from graphrag_kb_server.model.jwt_token import JWTTokenData, JWTToken
from graphrag_kb_server.service.jwt_service import generate_token


def generate_token_main(name: str, email: str, token_file: str):
    token = asyncio.run(generate_token(JWTTokenData(name=name, email=email), False))
    if isinstance(token, JWTToken):
        print("Token:")
        print(token.token)
        with open(token_file, "wt") as f:
            f.write("# Administration Token\n\n")
            f.write("- Token: ")
            f.write(token.token)
            f.write("\n- Name: ")
            f.write(name)
            f.write("\n- Email: ")
            f.write(email)
        admin_yaml = f"""
administrators:
  - {email}
"""
        print("\nAdministration YAML:")
        print(admin_yaml)
        print("\nUpdate your config/administration.yaml file with this email address.")
        # TODO: Update the administration.yaml programmatically.
    else:
        print("Could not generate token.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates the administrator's token and prints it on the console")
    parser.add_argument("name", type=str, help="The name of the administrator or organisation")
    parser.add_argument("email", type=str, help="The email of the administrator or organisation")
    parser.add_argument("token_file", nargs='?', type=str, help="The file which will store the administration token")
    args = parser.parse_args()

    token_file = args.token_file or "admin_token.md"
    generate_token_main(args.name, args.email, token_file)