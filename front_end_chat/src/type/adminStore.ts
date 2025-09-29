export type AdminStore = {
	tennants: Tennant[] | null;
	loadTennants: (jwt: string) => Promise<void>;
	createTenant: (jwt: string, tenantData: { tennant_name: string; email: string }) => Promise<void>;
	deleteTenant: (jwt: string, tenantId: string) => Promise<void>;
};

export type Tennant = {
	folder_name: string;
	creation_timestamp: string;
	token: string;
	visualization_url: string;
	chat_url: string;
};
