export type AdminStore = {
	tennants: Tennant[] | null;
	loadTennants: (jwt: string) => Promise<void>;
};

export type Tennant = {
	folder_name: string;
	creation_timestamp: string;
	token: string;
	visualization_url: string;
	chat_url: string;
};
