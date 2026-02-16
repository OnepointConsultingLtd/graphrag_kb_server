import type { Project } from "../model/projectCategory";
import type { Reference } from "../model/references";
import type { Topics, Topic } from "../model/topics";
import { getBaseServer } from "./server";
import type { Query } from "../model/query";
import type { ChatMessage } from "../model/message";
import { ChatMessageTypeOptions } from "../model/message";
import { GenerateDirectUrlRequest } from "../model/generateDirectUrl";

function createHeaders(jwt: string) {
  return {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    },
  };
}

function createBaseUrlParams(project: Project) {
  const params = new URLSearchParams();
  params.set("project", project.name);
  params.set("engine", project.platform);
  return params;
}

async function processError(response: Response) {
  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ description: `HTTP error! status: ${response.status}` }));

    throw new Error(
      errorData.description || `HTTP error! status: ${response.status}`,
    );
  }
}

export async function validateToken(token: string) {
  const response = await fetch(
    `${getBaseServer()}/token/validate_token?token=${token}`,
    {
      method: "POST",
      headers: {
        ...createHeaders(token).headers,
      },
    },
  );
  if (!response.ok) {
    throw new Error(
      `Token validation failed. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function validateAdminToken(name: string, email: string, password: string) {
  const params = new URLSearchParams();
  params.set("name", name);
  params.set("email", email);
  params.set("password", password);

  const response = await fetch(
    `${getBaseServer()}/tennant/admin_token?${params.toString()}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `Admin login failed. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function fetchProjects(jwt: string) {
  try {
    const response = await fetch(
      `${getBaseServer()}/protected/projects`,
      createHeaders(jwt),
    );
    if (!response.ok) {
      throw new Error(
        `Failed to fetch projects. Error code: ${response.status}. Error: ${response.statusText}`,
      );
    }
    return await response.json();
  } catch (error: unknown) {
    // This block handles network-level errors (e.g., CORS, DNS, bad headers)
    if (error instanceof TypeError) {
      // Typical for network issues or CORS problems
      throw new Error(
        `Network error while fetching projects: ${error.message}`,
      );
    } else if (error instanceof Error) {
      // Re-throw known errors with more context
      throw new Error(`Unexpected error: ${error.message}`);
    } else {
      // Unknown failure mode
      throw new Error(`Unknown error during fetchProjects`);
    }
  }
}

export function convertChatHistoryToLightragChatHistory(
  chatHistory: ChatMessage[],
) {
  const maxSize = 10;
  return chatHistory
    .map((message) => ({
      role: message.type === ChatMessageTypeOptions.USER ? "user" : "assistant",
      content: message.text,
    }))
    .slice(0, maxSize);
}

export async function sendQuery(query: Query) {
  const { jwt, question, project, chatHistory, conversationId } = query;
  const params = new URLSearchParams();
  params.set("project", project.name);
  params.set("engine", project.platform);
  const response = await fetch(
    `${getBaseServer()}/protected/project/chat?${params.toString()}`,
    {
      ...createHeaders(jwt),
      method: "POST",
      headers: {
        ...createHeaders(jwt).headers,
      },
      body: JSON.stringify({
        question: question,
        search: project.search_type,
        format: "json",
        context_size: 14000,
        system_prompt_additional: project.additional_prompt_instructions,
        include_context: true,
        structured_output: true,
        chat_history: convertChatHistoryToLightragChatHistory(chatHistory),
        conversation_id: conversationId,
      }),
    },
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch projects. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function downloadFile(
  jwt: string,
  project: Project,
  reference: Reference,
  originalFile: boolean = false,
): Promise<Response> {
  return await downloadFilePath(jwt, project, reference.path || "", originalFile);
}

export async function downloadFilePath(
  jwt: string,
  project: Project,
  path: string,
  originalFile: boolean = false,
): Promise<Response> {
  const params = createBaseUrlParams(project);
  params.set("file", path);
  params.set("summary", "false");
  if (originalFile) {
    params.set("original_file", "true");
  }
  const response = await fetch(
    `${getBaseServer()}/protected/project/download/single_file?${params.toString()}`,
    createHeaders(jwt),
  );
  if (!response.ok) {
    throw new Error(
      `Failed to download file. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return response;
}

export async function uploadIndex(jwt: string, formData: FormData) {
  const response = await fetch(
    `${getBaseServer()}/protected/project/upload_index`,
    {
      method: "POST",
      body: formData,
      headers: {
        Authorization: `Bearer ${jwt}`,
      },
    },
  );

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ message: "An unknown error occurred." }));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`,
    );
  }
}

export async function generateSnippet(jwt: string, requestBody: object) {
  return await createPostBodyRequest(
    jwt,
    requestBody,
    "/protected/snippet/generate_snippet",
  );
}

async function createPostBodyRequest(
  jwt: string,
  requestBody: object,
  targetUrl: string,
) {
  const response = await fetch(`${getBaseServer()}${targetUrl}`, {
    method: "POST",
    ...createHeaders(jwt),
    body: JSON.stringify(requestBody),
  });

  await processError(response);

  return await response.json();
}

export async function deleteProject(
  jwt: string,
  project: string,
  engine: string,
) {
  try {
    const response = await fetch(
      `${getBaseServer()}/protected/project/delete_index?project=${project}&engine=${engine}`,
      {
        method: "DELETE",
        ...createHeaders(jwt),
      },
    );

    if (!response.ok) {
      throw new Error(
        `Failed to delete project. Error code: ${response.status}. Error: ${response.statusText}`,
      );
    }
    return await response.json();
  } catch (error: unknown) {
    throw new Error(`Failed to delete project. Error: ${error}`);
  }
}

function topicRequestFactory(project: Project, limit: number = 12) {
  const params = createBaseUrlParams(project);
  params.set("limit", `${limit}`);
  params.set("add_questions", "false");
  return params;
}

export async function fetchTopics(
  jwt: string,
  project: Project,
  limit: number = 12,
): Promise<Topics> {
  const params = topicRequestFactory(project, limit);
  params.set("entity_type_filter", "category");
  const response = await fetch(
    `${getBaseServer()}/protected/project/topics?${params.toString()}`,
    createHeaders(jwt),
  );

  await processError(response);

  return (await response.json()) as Topics;
}

export async function generateDirectUrl(
  jwt: string,
  requestBody: GenerateDirectUrlRequest,
) {
  return await createPostBodyRequest(
    jwt,
    requestBody,
    "/protected/url/generate_direct_url",
  );
}

export async function fetchRelatedTopics(
  jwt: string,
  project: Project,
  limit: number = 12,
  source: string,
  text: string,
) {
  const params = createBaseUrlParams(project);
  const requestBody = {
    source: source,
    text,
    limit: limit,
    similarity_topics_method: "nearest_neighbors"
  };

  const response = await fetch(
    `${getBaseServer()}/protected/project/related_topics?${params.toString()}`,
    {
      method: "POST",
      ...createHeaders(jwt),
      body: JSON.stringify(requestBody),
    },
  );
  await processError(response);
  return (await response.json()) as Topics;
}

export async function downloadTopics(jwt: string, project: Project) {
  const params = createBaseUrlParams(project);
  params.set("format", "csv");
  params.set("limit", "100000");
  const response = await fetch(
    `${getBaseServer()}/protected/project/topics?${params.toString()}`,
    createHeaders(jwt),
  );
  if (!response.ok) {
    throw new Error(
      `Failed to download topics. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return await response.blob();
}

export async function generateQuestions(
  jwt: string,
  project: Project,
  topic: Topic,
) {
  const params = createBaseUrlParams(project);
  const requestBody = {
    topics: [topic.name],
    text: "",
    topic_limit: 10,
    entity_type_filter: topic.type,
    format: "json",
    system_prompt: "",
  };
  const response = await fetch(
    `${getBaseServer()}/protected/project/questions?${params.toString()}`,
    {
      method: "POST",
      ...createHeaders(jwt),
      body: JSON.stringify(requestBody),
    },
  );
  if (!response.ok) {
    throw new Error(
      `Failed to generate questions. Error code: ${response.status}. Error: ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function tennantApiTemplate(
  jwt: string,
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  requestBody?: object,
) {
  const config: RequestInit = {
    method,
    ...createHeaders(jwt),
  };

  if (requestBody && (method === "POST" || method === "PUT" || method === "DELETE")) {
    config.body = JSON.stringify(requestBody);
  }

  const response = await fetch(
    `${getBaseServer()}/protected/tennant/${endpoint}`,
    config,
  );

  if (!response.ok) {
    const errorMessage = await response.text().catch(() => response.statusText);
    throw new Error(
      `Failed to ${method.toLowerCase()} tenant. Error code: ${response.status}. Error: ${errorMessage}`,
    );
  }

  const data = await response.json();
  return data;
}

export async function listTennants(jwt: string) {
  return await tennantApiTemplate(jwt, "list_tennants", "GET");
}

// Create tenant
export async function createTenant(
  jwt: string,
  tenantData: { tennant_name: string; email: string }
) {
  return await tennantApiTemplate(jwt, "create", "POST", tenantData);
}

// Delete tenant
export async function deleteTenant(
  jwt: string,
  tenantData: { tennant_folder: string }
) {
  console.log("deleteTenant", tenantData);
  return await tennantApiTemplate(jwt, "delete_tennant", "DELETE", tenantData);
}
