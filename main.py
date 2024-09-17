import os
import uvicorn
from pydantic import BaseModel, Field
from typing import Optional, List

import vertexai
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions
from vertexai.preview.generative_models import (
    GenerativeModel,
    Part, 
    SafetySetting,
    Tool,
    grounding,
)
import vertexai.generative_models as generative_models

if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()


from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

project_id = os.environ.get('PROJECT_ID', 'nuttee-lab-00')
location = os.environ.get('LOCATION', 'us-central1')
search_engine_id = os.environ.get('SEARCH_ENGINE_ID', 'pruksa-ariba-docx_1726550516515')
datastore_location = os.environ.get('DATASTORE_LOCATION', 'global')
datastore_id = os.environ.get('DATASTORE_NAME', 'pruksa-ariba-docx_1726550516515')


vertexai.init(project=project_id, location=location)

# Gemini configurations
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

app = FastAPI()
app.project_id = project_id
app.location = location

templates = Jinja2Templates(directory="templates")

class SearchQueryPayload(BaseModel):
    search_query: str
    engine_id: str = Field(default="pruksa-ariba-docx_1726550516515", description="The engine ID (optional)")
    datastore_project_id: str = Field(default="nuttee-lab-00", description="The datastore project ID (optional)")
    datastore_loc: str = Field(default="global", description="The datastore location (optional)")
    model_version: str = Field(default="gemini-1.5-flash-001/answer_gen/v2", description="The model version (optional)")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search")
async def search_with_answer(payload: SearchQueryPayload) -> str:
    search_query = payload.search_query
    engine_id = payload.engine_id
    datastore_project_id = payload.datastore_project_id
    datastore_loc = payload.datastore_loc
    model_version = payload.model_version

    # Create a client
    #  For more information, refer to:
    # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    client_options = (
        ClientOptions(api_endpoint=f"{datastore_loc}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    # The full resource name of the search app serving config
    serving_config = f"projects/{datastore_project_id}/locations/{datastore_loc}/collections/default_collection/dataStores/{engine_id}/servingConfigs/default_config"

    # Optional: Configuration options for search
    # Refer to the `ContentSearchSpec` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        # For information about snippets, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        # SearchResultMode https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/SearchResultMode
        #search_result_mode=discoveryengine.SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
        # For information about search summaries, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            #model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
            #    preamble="YOUR_CUSTOM_PROMPT"
            #),
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version=model_version,
            ),
        ),
    )

    # Refer to the `SearchRequest` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)

    return response.summary.summary_text

@app.get("/gemini_grounding")
async def gemini_grounding(
    search_query: str,
    model_version: str = "gemini-1.5-pro",
    grounding_datastore_id: str = datastore_id,
    grounding_datastore_location: str = datastore_location,
    grounding_project_id: str = project_id,
) -> str:
    model = GenerativeModel(
        model_name=model_version,
    )

    grounding_tool = Tool.from_retrieval(
            grounding.Retrieval(
                grounding.VertexAISearch(
                    datastore=grounding_datastore_id,
                    project=grounding_project_id,
                    location=grounding_datastore_location,
                )
            )
        )

    # Generate content using the assembled prompt. Change the index if you want
    # to use a different set in the variable value list.
    responses = model.generate_content(
        [search_query],
        tools=[grounding_tool],
        generation_config=generation_config,
        safety_settings=safety_settings,
    )

    return responses.text

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
