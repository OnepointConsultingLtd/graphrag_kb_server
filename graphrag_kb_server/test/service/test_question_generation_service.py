import asyncio
from graphrag_kb_server.model.topics import Topic, Topics
from graphrag_kb_server.service.question_generation_service import generate_questions


def test_generate_questions():

    topics = Topics(
        topics=[
            Topic(
                name="AI",
                description="""AI (Artificial Intelligence) is a dominant and rapidly advancing field of computer science and technology focused on creating intelligent machines and systems capable of performing tasks that typically require human intelligence, replicating or improving human cognitive function, and mimicking human actions. Celebrating its 70th anniversary, AI is a broad field encompassing various technologies, including machine learning (ML), symbolic AI, generative AI, rule-based AI, general-purpose AI, narrow domain AI tools like ChatGPT and Large Language Models (LLMs), deep learning, decision intelligence, knowledge graphs, and neuro-symbolic AI, with a long and rich history and diverse techniques. AI encompasses both symbolic and sub-symbolic approaches, including machine learning and neural networks, and is evolving towards neuro-symbolic AI for explainability and trust.

AI encompasses sensing, thinking, acting, and learning capabilities, thriving on raw source data to uncover hidden insights, analyze data, and extract valuable insights, driving critical, high-value decisions based on complex data and solving problems related to unstructured data. It is used to automate tasks, improve customer service, optimize business processes, identify, onboard, service, and secure new business customers. AI is used to crunch statistics and reveal insights about various markets, interpret data and anticipate future needs, and predict maintenance needs based on sound recognition. It can calculate the likelihood of resolving issues and provide real-time updates and options to customers during a crisis. AI is also used to make sense of data without cleaning it.

AI is used to improve customer experiences, remove customer frustrations, enhance customer service, and even make customer service models invisible. Furthermore, AI enhances systems, resolves user queries, identifies areas for knowledge improvement, manages and motivates remote sales forces, and is applied in various fields, such as enabling a more sustainable system of energy production, distribution, and consumption, and creating responsive supply chains in conjunction with technologies like blockchain and digital twins. Specifically, Deep Learning, a subset of AI, is being used to improve sales forecasting accuracy. AI is used in revenue intelligence platforms to identify and promote successful sales behaviors, for forensic analysis and automating complex decision-making, outperforming human intelligence in anomaly detection, and to power digital audit platforms, such as Vyntelligence's digital audit platform, enabling analysis of video/audio data and identification of high-risk sites and issues. HSBC also utilizes AI to enhance the investor market, in risk transformation and innovation. Rainbird also uses AI to address various issues, and to capture human knowledge and automate decision making. AI is also used to make sense of process complexity in the public health service transformation. Zuhlke uses AI to analyze data, develop a prototype app, and potentially save the online retail sector. CloudApps uses AI to help sales managers predict and improve sales results, and Iris Software uses AI for deal prediction, to improve sales forecasting and identify best practices. Be Informed uses AI to translate regulatory requirements into machine-readable models and to drive semantic modeling and advanced automation in compliance systems. Sensai uses AI as the core technology behind its predictive capabilities and guided selling features. Filament uses AI in its solutions for knowledge management, automation, and research. RequirementONE also leverages AI to power its platform, enabling automated tasks, real-time insights, and advanced analysis in regulatory compliance. DAIKIN uses AI to monitor and control operational statuses remotely.

AI is also used in chatbots for natural language processing, understanding user intent, and providing relevant responses, as well as by Netflix for content discovery and consumption. Moreover, AI is a tool to search for the possible and overcome constraints in data analysis, and is used for knowledge management, connecting data, and improving knowledge base content. AI is a significant technology offered by solution providers and a topic of executive briefings. AI is used to improve sales performance, automate complex processes, enhance customer service, and enhance sales and marketing strategies. It is expected to improve customer satisfaction, reduce attrition, and enhance first-call resolution rates, and is seen as a positive force for visionary companies. AI is mentioned in the context of AI-driven bots taking away customer complexity and the increasing AI landscape. AI is used in business to reimagine survival and success.

While AI is rapidly progressing and impacting various industries, including software development and the legal industry (automating services, drafting contracts, and enhancing legal work), concerns have been raised about its potential dangers, including potential threats to the job market. The future development of AI is uncertain, with debates on whether it will be achieved in the next decade, century, or ever. Some view AI skeptically, while Ock is an early practitioner of the field. AI is used to create solutions for various business needs. AI is the topic of the 35th Innovation Talk, causing both excitement and confusion, and a future Innovation Talk in November, specifically its impact on software engineering and focusing on its predictive capabilities. It is mentioned in the context of Shaping Tomorrow's tools and a question about its combination with Quantum Computing. AI is the central topic of the talk, focusing on its application to solve critical business problems and improve software productivity. AI is a technology being explored to address business challenges exposed by the Covid-19 pandemic.

AI is one of the three key topics (AI, Data, and Emerging Tech) that will be covered in quarterly briefings starting in January. AI is mentioned as something to be careful of regarding behavioral measurement bias. AI is a technology being applied to data, but which can exacerbate existing biases if safeguards are not in place. Sophisticated AI is mentioned in the context of 'garbage in, garbage out' and the importance of addressing bias.

Origami Labs develops and applies AI, particularly in defense and security.

AI is used to identify medical conditions like cardiac arrest and stroke, and to analyze data for insights, and for decision support and other applications, particularly in healthcare.

AI is used in solution printing and is also mentioned as a potential enemy of climate change due to increased energy costs.

AI is used in conjunction with other technologies to facilitate growth and to facilitate dynamic supply chains.

AI is a key topic, overlapping with data privacy and security, and exemplified by technologies like Chat GPT and Claude.

AI is used for decision-making and auditing, but also subject to auditing itself.

AI can play a role in customer lifecycle intelligence.

AI is used to capture human knowledge and automate decision making.

AI is a field requiring specialized skills for development and implementation.

AI is used in revenue intelligence platforms to predict outcomes, qualify deals, and maximize growth through data analysis and machine learning.

AI is mentioned in the context of engineering and its potential for over-complication. It is also used to accelerate engineering research and development, create models, optimize designs, and reduce simulations and testing.

AI is used to predict customer retention risks and provide data-driven insights.

AI is used for data analysis and insights in sales and operations.

AI can be integrated with connected worker platforms to enhance decision-making.

AI, encompassing machine learning and other forms of machine intelligence, is used for analyzing and creating data.

AI is the broader field to which generative AI belongs.

AI is the main topic of discussion, encompassing machine learning, ethical considerations, and public perception.

AI is a field that organizations are trying to embrace, leading to the hiring of data scientists and the formation of blended skillset teams.

AI is the capability of a machine to imitate intelligent human behavior.

AI is mentioned as an example of a technology that caught people by surprise.

AI is used in conjunction with sensors and data to make insights and decisions, either autonomously or with human involvement.

AI is a top priority technology, unlike Quantum Computing which is still developing, but is expected to merge with quantum computing in the future.

AI is a complex topic to be discussed in a future event.

AI, specifically its impact on software engineering, is the main topic of discussion.

AI is the technology that the machine uses to process information and generate reports.

AI is being used for analysis, summarization, and generating content.

AI is a key topic of discussion, especially its combination with human intelligence.

AI is used in the strategic foresight tool to synthesize information and provide insights.

AI is used in the machine to provide input alongside human input for synthesis.

AI is discussed as a catalyst and sparring partner that empowers teams to be more efficient.

AI is being explored to think about customer experience more holistically.

AI was used as a tool in various stages of the productive sprint but was found lacking in depth and nuance during the ideation session.

AI is used as a tool to improve efficiency and effectiveness in various tasks, including retail returns processing.

AI is used to collect data from purchasers' past history and other users with similar sizing to provide size recommendations.
""",
                type="category",
            ),
            Topic(
                name="Be Informed",
                description="""Be Informed is an internationally operating, independent software vendor and a leading provider of intelligent compliance solutions, specializing in dynamic/intelligent processes. They are recognized as a market leader in Dynamic/Adaptive Case Management. Be Informed offers a disruptive, next-generation Business Process Platform that utilizes semantic technology to model and execute business processes, policies, and regulations. Their platform is designed to enable organizations to design, manage, and analyze all aspects of their business, automate business processes, improve flexibility and responsiveness, and enhance customer experience. It allows businesses to create models that can be directly implemented, tested, and adjusted, emphasizing business agility and the use of a single business language. The technology is described as 'cool', 'elegant' and 'potentially disruptive'.

Be Informed focuses on model-driven development and customer involvement, offering a direct model-driven platform and using one business language to change the process paradigm. Their platform supports all aspects of the policy lifecycle and provides an ecosystem for sharing and reuse. It offers a single environment where business knowledge resides in a single model, allowing for high productivity and automated decision making. The platform enables the capturing of ideas, requirements, scenarios, activities, and business rules in models, allowing for rapid business prototyping and quick validation of business ideas. It embeds compliance into business processes, turning it from a burden into an advantage. The platform supports administrative processes with a focus on dynamic case management, connecting legacy systems and automating compliance tracking. It integrates with existing systems using services, messages, or files, focusing on complex knowledge work and process automation. Be Informed is also recognized as best in class for Dynamic Case Management.

Be Informed offers an intelligent robotic process automation product that automatically generates customer and employee processes, and interprets rules at run time. Its orchestrator application has been used by Brabant Water to connect legacy systems and ensure seamless compliance management. Tesco Bank has also used their product to create customer journeys. Be Informed was also called in by ABN AMRO Bank to solve the bereavement handling problem, and partnered with ABN AMRO to deliver the case management system supporting the Bereavement Desk. The company aims to provide cost savings, improved productivity, and faster time-to-change for organizations.

The Be Informed platform supports overlay applications, data mapping, dashboards, and reporting. It provides an Integrated Development Environment (IDE) and integrates with various systems using open standards. It is a case management application that provides auditing, logging, and monitoring capabilities. It supports communication security through PKI and has specific system requirements for its Studio and Server Application components. Be Informed also provides solutions for enterprise search, business intelligence, and data warehousing.

Be Informed specializes in solutions for the public sector, financial services, and regulated industries. They recommend upgrading Java and Windows Server versions. Their Service Oriented Architecture is based on self-contained components (building blocks) that independently provide particular functions (services) to other components. The case management application supports multiple channels and security features. Jeff Ashbolt is the UK Country Head at Be Informed, and the company is involved in the IPA event as a potential presenter.

Be Informed is a project management company responsible for the development of the National Planning Portal. It is used by Brabant Water and the European Patent Office for business transformation and process improvement. Be Informed worked with EPO to customize its software and is a major component of INDiGO. It also delivered a one-stop-shopping portal for licenses in The Netherlands. Be Informed partnered with BearingPoint for the Caribbean Netherlands Tax Administration project and enabled CACI to compress development lifecycles. It also worked with P&G to develop a Global Product Clearance solution.

Be Informed has observed two different approaches to organizational change: Business Result focus and Business Transformation focus. Be Informed is a system that integrates with CRM systems like Dynamics CRM to provide enhanced decision support and customer context analysis. Be Informed is a system that operates 'above the layers' in a system structure, using open standards to integrate with enterprise services. It is declarative in execution and uses backward chaining goal orientation to execute activities. It treats human and automated workflow activities in the same way and can co-exist with an ESB based architecture.

Be Informed provides business solutions for organizations with knowledge-intensive and complex administrative processes. It challenges traditional system architecture and simplifies application architecture through its compact self-contained engine and model-driven language. It allows organizations to engage in customer-driven dialogues and supports administrative professionals' decision-making. Be Informed provides domain-specific business solutions based on a semantic business process platform, enabling public sector and financial services institutions to achieve breakthrough business results.

Be Informed provides technology for complex and networked environments, focusing on model-driven business applications. It competes with companies like Oracle, Pega, IBM, Tibco, SAP, and Oracle Applications. Be Informed provides the Multi Benefit Solution and Semantis platform for public service agencies. It works with partners for implementation and acts as a trusted advisor. It prefers a subscription model for its licenses and applies value-based pricing.

Be Informed develops products and maintains a roadmap to guide their development. It focuses on business design, policy lifecycle, sharing and reuse, model-driven services, and a modular, service-oriented architecture. Be Informed provides services across environments and intends to extend its capabilities in various directions, including webscale process, finding black swans, cloud of services, integrated method, and collaborative modeling. Be Informed supports creative modeling of business solutions and has a business process platform. Be Informed also partnered with TBAS to develop the Loan Modification Management Solution (LMMS).

Be Informed provides a Multi-channel Sales Platform and an Intelligent Claims Processing Engine, developed in cooperation with subject matter experts. They work with financial service companies like AEGON Turkey and Achmea to develop and implement solutions for sales and claims processing. Be Informed is also the provider of the business process platform selected by CAK to implement the required applications for the WTGC Act, and partnered with WTCG to implement required applications.

Be Informed believes technology should adapt to people and aims to provide quality and speed of service, enabling knowledge workers to record their business knowledge. Be Informed is a competitor to Oracle, offering a model-driven decision management engine. It is known for cost savings, higher straight-through processing rates, and reduced time-to-change.

Be Informed captures process by focusing on the constraints. Be Informed designed the Welfare Advice Service system and is being considered for the Rules Engine for the core Immigration Platform. Be Informed provides the OM with a business process platform for complex and knowledge-intensive administrative processes and was selected as the supplier for the Business Rules Engine.

Be Informed is a system that allows users to create immediately executable applications without code generation or intermediate steps. It separates knowledge from the flow of business processes, using a non-linear approach with activities constrained by conditions.

Be Informed is an integrated business platform built from the ground up as one integrated stack, allowing business users to define all aspects of their business in one integrated semantic model.
""",
                type="organization",
            ),
        ]
    )
    topic_questions = asyncio.run(generate_questions(topics))
    assert len(topic_questions.topic_questions) == 2
    for topic_question in topic_questions.topic_questions:
        print(f"Topic: {topic_question.name}")
        for question in topic_question.questions:
            print(f"  - {question}")
        print()
