from enum import Enum
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.ai_provider.ai_provider import init_llm_by_provider
from src.logging.logging import get_logger

logger = get_logger(__name__)


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class Evidence(BaseModel):
    path: str = Field(examples=["services/orders/build.gradle.kts"], description="Path to the file to be evidenced.")
    snippet: str = Field(examples=["implementation(\"org.springframework.boot:spring-boot-starter-web:3.2.5\""],description="Snippet of the file to be evidenced.")
    reason: str = Field(examples=["Dependency pin to Spring Boot starter"], description="Reason for the evidence.")

class TechStack(BaseModel):
    name: str = Field(description="Technology, framework, or library name")
    version: str = Field(description="Version of the technology, if available")
    evidence: List[Evidence] = Field(description="List of evidence objects")
    confidence: ConfidenceLevel = Field(description="Confidence level in tech stack identification, based on the evidences found")

class TechStackResult(BaseModel):
    tech_stacks: List[TechStack] = Field(description="List of tech stacks with name and version")

def tech_stack_agent(dependency_file_content: str) -> TechStackResult:
    """
    Analyze a dependency management file and return a list of tech stacks used, including name and version.
    """
    parser = JsonOutputParser(pydantic_object=TechStackResult)
    prompt_text = """
        SYSTEM: You must reply ONLY with a valid JSON object matching the output schema below.
        Given the content of a dependency management file, analyze and extract the list of major technologies, frameworks, platforms, or languages used by the project and their versions.

        - Prioritize the following list of technologies, frameworks, and platforms when extracting tech stacks (but do not limit to it alone):
        [
            "ctix Web", "Adobe Commerce", "AIOHTTP", "Akka", "Ambiorix", "Angular", "Apache HttpClient", "Apache HttpCore",
            "Apache Log4j API", "ASP.NET", "ASP.NET Core", "Aura", "Aurelia", "Axum", "Azure OpenAI SDK", "Backbone.js",
            "Beego", "Blazor", "Bootstrap", "Bottle", "breakr", "Buffalo", "Bulma", "CakePHP", "Cf Java Logging Support Core",
            "Chai", "CherryPy", "Chi", "CMS", "CodeIgniter", "CubicWeb", "Cypress", "Dash", "Database", "Dioxus", "Django",
            "Dropwizard", "Drupal", "Echo", "Elasticsearch", "Electron", "Ember.js", "Enzyme", "Express", "Falcon", "FastAPI",
            "Fastify", "Fat-Free Framework", "Fiery", "Flask", "Flight", "FuelPHP", "Gatsby", "Gin", "Giotto", "Goji", "goqu",
            "Gorilla", "Grails", "Grape", "Grok", "Growler", "Guava", "Hanami", "Hibernate", "Hug", "Iced", "Inferno",
            "Jasmine", "Javalin", "JDBI", "Jersey", "Jest", "JHipster", "Joomla!", "jQuery", "Juniper", "Junit", "Kitura",
            "knex", "Knockout", "Kohana", "kotest", "Ktor", "Kweb", "Lagom", "Laminas Project", "Laravel",
            "LiftWeb", "Lithium", "Logback Classic Module", "MariaDB", "Martini", "Masonite",
            "Medoo", "Meteor", "Micronaut", "MobX", "Mocha", "MongoDB", "Morepath", "MyBatis", "MySQL", "Nagare", "NestJS",
            "Nette", "Next.js", "Nuxt", "October CMS", "Phalcon", "Phoenix", "PHPixie", "PHP-MVC", "Play", "PlayWright",
            "Polymer", "PostgreSQL", "Preact", "PrestaShop", "Project Lombok", "Prophecy", "Protractor", "Pyramid", "Quarkus",
            "Quart", "Qwik", "Ratpack", "React", "Reahl", "Redis", "Redux", "Remix", "Responder", "Revel", "Rocket",
            "Ruby on Rails", "Sanic", "Sass", "Semantic UI", "Sequelize", "Shiny for R", "Silex", "Sinatra", "Slim",
            "SolidJS", "Spark", "Spring Boot", "SQLite", "SQL Server", "Stencil", "Struts", "Svelte", "Swagger UI",
            "Symfony", "Tailwind CSS", "Tauri", "Thymeleaf", "Tokio", "TurboGears", "TypeORM", "Vaadin Framework", "Vapor",
            "Vavr", "Vert.x", "Vitest", "Vue.js", "Warp", "Web2py", "Web.go", "Wicket", "WordPress", "Yew", "Yii", "Zope",
            "ZURB Foundation"
        ]
        - Only include major frameworks, platforms, languages, or umbrella technologies (e.g., Spring Boot, Django, React, Node.js, PostgreSQL, Java, TypeScript, etc.).
        - Do NOT include low-level dependencies, utility libraries, or drivers (e.g., do not include 'pg', include 'PostgreSQL'; do not include 'mysql-connector', include 'MySQL').
        - You can use string matching to identify technologies from the dependency file content.
        - If a dependency is a driver or adapter, map it to its umbrella technology.
        - In a Gradle or POM file, if you find a task with useJUnitPlatform(), map it to 'Junit'.
        - Map any dependency containing 'junit', 'JUnit', or 'org.junit' to 'JUnit'.
        - Map any dependency containing 'kotest' or 'Kotest' to 'Kotest'.
        - Map any dependency containing 'guava' or 'Guava' to 'Guava'.
        - Map any dependency containing 'guava' or 'Guava' to 'Guava'.
        - Map any dependency containing 'log4j' to 'Apache Log4j API'.
        - Map any dependency containing 'fastify' to 'Fastify'.
        - Map any dependency containing 'openapi' to 'Swagger UI'.
        - If you find a dependency with a groupId, artifactId or package that has 'io-swagger.core' or 'swagger', map it to 'Swagger UI'.
        - If you find a dependency with a groupId, artifactId or package that contains 'ch.qos.logback' or 'net.logstash.logback', map it to 'Logback Classic Module'.
        - If you find a dependency with a name containing '@nestjs/platform-express', map it to both 'NestJS' and 'Express'.
        - If you find a dependency with a groupId, artifactId, or package containing 'hypersistence' or 'hibernate', map it to 'Hibernate'.
        - In a package.json file, if you find the dependency 'pg', map it to 'PostgreSQL'.
        - If no umbrella technology exists, include the library name (e.g., Jest, Knex, Chai).
        - Return a list of technology names with their versions.
        - If you cannot extract any tech stack, return an empty array for 'tech_stacks'.
        - Provide also the evidence and the confidence for each tech stack found
        
        ### Confidence Specification
        Each detected technology must include a `"confidence"` object with the following structure:
        - `"level"`: one of `"high"`, `"medium"`, `"low"`, `"none"`.
        - `"high"` → clear, explicit evidence (e.g., direct dependency match or version found).
        - `"medium"` → partial or indirect evidence (e.g., related plugin or alias).
        - `"low"` → speculative or weak evidence (e.g., mentioned in comments, uncertain mapping).
        - `"none"` → no reliable evidence.
        
        - `"evidence"`: a short explanation of what was found that supports this identification.
        
        USER: Here is the content of a dependency management file:
        {dependency_file_content}
        
        ## Output
        {format_instructions}
        
        """

    prompt = PromptTemplate(
        template=prompt_text,
        input_variables=["dependency_file_content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    llm = init_llm_by_provider()
    chain = prompt | llm | parser

    try:
        response = chain.invoke({"dependency_file_content": dependency_file_content})
    except Exception as e:
        logger.warning(f"tech_stack_agent failed to parse output: {e}")
        response = TechStackResult(tech_stacks=[])

    logger.info(f"Tech stack LLM output: {response}")
    return response
