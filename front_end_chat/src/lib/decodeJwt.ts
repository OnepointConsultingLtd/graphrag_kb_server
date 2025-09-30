
import { jwtDecode } from "jwt-decode";
import type { decodedJwt } from "../type/decodedJwtType";

export default function decodedJwt(jwt: string): decodedJwt {
	const decoded = jwtDecode(jwt);
	return decoded as decodedJwt;
}

