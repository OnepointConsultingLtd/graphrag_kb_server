# What is the vision of the AI Engine?

The AI Engine should provide all you need to be able to understand and interact with different sets of documents you might have: after uploading your documents in your tennancy you will be able to interact with your documents using a regular chatbot, a semantic search engine, a reverse chatbot that acts as topic drive smart advisor, a grahical chatbot or you will be able to visualize the nodes of the graph in a separate visualization tool.


What are the components?

- Smart Agent ingestion
	- function

		Based on a topic description, researches subtopics and finds relevant documents in these subtopics and extracts the relevant pieces of information whilst assigning clear metrics to the text that has been found.
	- tech description

		Uses components like deep research, OCR conversion and different techniques for metric based evaluation

- Dashboard
	- function
		
		The dashboard supports two roles: the administrator and the tennant roles. The administrator dashboard is only used to manage tennants and allocate disk space for them. The tennant dashboard allows to:

			1. create new projects by either uploading zipped documents or by triggering the Smart Agent Ingestion (see above). Creating a new project is synonymon for "Create index"
			2. start any of the tools provided by the AI Engine in order to play around with the content
			3. Provide reports on the uploaded projects (most important topics, topics communities)
	- tech description
		
		Uses multiple engines, like the GraphRAG, LighRAG engines and supports CAG (Cached Augmented Generation via Gemini)

- Create index
	- function

		This is a function of the dashboard which allows to upload a zip file with all of the PDF, text or markdown files of a project.
	- tech description

		The dashboard web application uses multiple engines, like the GraphRAG, LighRAG engines and supports CAG (Cached Augmented Generation via Gemini)

- Reverse chatbot with confidence calculation
	- function
		
		This is a topic focused chatbot (like a specialized consultant) which questions the end user sequentially around a specific topic domain, like "Data Gouvernance", "Responsible AI", "Agentic Workflows" and over time builds a confidence level that allows the chatbot to offer advice and also suggest to connect to human consultants.
	- tech description

		The reverse chatbot is a web application which interacts with the AI engine to generate context for each generated question. It has its own internal database which gathers information about all interactions that is also used as a form of memory to calculate the confidence level.

	Link: https://responsible-ai.onepointltd.ai/1?id=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMUpKUDlRQldLNTNFQ0NIVFY4U1pOV0cyWSIsIm5hbWUiOiJTaGFzaGluIFNoYWgiLCJpYXQiOjE3MzgwNjI2NzF9.ASBqPULFthHrPCTJFzn4cuSiwRfiiUProeXQo1UgiUY

- Smart document search

	- function

		Based on profile data and selected topics you can search for documents in the knowledge graph. The documents are retrieved by personalized relevance and summarized in the context of the profile.
	- tech description

		This module searches for entities in the knowledge graph based on the profile of a user and then narrows down the search to these entities based on the profile which might be extracted from LinkedIn.

	Link: https://clustre.onepointltd.ai/

- Topic Driven Chatbot (OSCA)
	- function

		Graphical chatbot with related topics suggestion and topic based question generation. This tool can be customized to interact with the end user using different customizable behaviours.
	- tech description

		This chatbot relies on the internal RAG system and knowledge graphs for topic extraction and question generation.

	link: https://osca.onepointltd.ai/
- Normal chatbot
	- function

		Simple chatbot functionality with references, suggestion topics, automated question generation which can be used explore each of the document sets. This is directly integrated with the dashboard and requires minimal configuration, so this is used as a tool to quickly preview the quality of the dataset.
	- tech description

		Interacts with the RAG system and the knowledge graph to produce the conversation, related topics and question generation.

	Link: https://engine.onepointltd.ai/chat?project=clustre_full&platform=lightrag&search_type=local&token=eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJnaWxfZmVybmFuZGVzIiwibmFtZSI6ImdpbF9mZXJuYW5kZXMiLCJpYXQiOjE3NTcxNTQ1NzMsImVtYWlsIjoiZ2lsLmZlcm5hbmRlc0BvbmVwb2ludGx0ZC5jb20iLCJwZXJtaXNzaW9ucyI6WyJyZWFkIl19.-36WSJ27adexCgd5r5S-WdxayMaMS9v0C8eXKAeGlTU47MzT77jE4h0g32GmOjO6i2jzVyVF3MvQ11pfispLZQ&chat_type=chat&streaming=false
- Visualization / Reporting
	- function

		Basic graph visualization to give an overwiew of the uploaded sets of documents.
	- tech description

		Simple web application which allows to entities and relationships of the uploaded document sets.

- Back-end services
	- function

		These are REST interfaces and some websocket interfaces with all of the functionality of the AI engine, including:

			1. Content indexing and index management (delete, update index)
			2. Semantic context query
			3. Question Answering
			4. Related topic generation
			5. Topic based question generation
			6. Document search
			7. PDF generation
			8. LinkedIn profile scraping
	- tech description

		The back-end services are all technical interfaces document with Swagger.

	Link: https://engine.onepointltd.ai/docs

What is novel (innovation paragraph)?

This is a multi-tennant fully integrated solution which offers a full range of tools around your data which is internally represented as a knowledge graph. You get in one package a research agent associated to a smart advisor, two chatbots, a search engine, visualization tools that you can use as is or integrate into existing webpages or other services.


2025-11-12

- generational use cases: automated use cases, propositions, learning materials, webpages, business opportunities generator
- pluggable use cases
- ingestional: extractional tools