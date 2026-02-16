import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

# Import RAG retrieval
from vectorstore.chroma_store import retrieve_relevant_docs

load_dotenv()


def generate_sar_narrative(data, rule_result):
    """
    Generates SAR narrative using:
    - Case data
    - Triggered compliance rules
    - Retrieved regulatory guidance (RAG)
    """

    # Initialize Ollama LLM
    llm = OllamaLLM(model=os.getenv("OLLAMA_MODEL"))

    # ---------------------------------------------------
    # 🔎 STEP 1: Retrieve Regulatory Context (RAG)
    # ---------------------------------------------------
    retrieved_docs = retrieve_relevant_docs(
        "SAR filing thresholds structuring regulation investigation documentation requirements"
    )

    # Flatten retrieved results
    regulatory_context = ""
    if retrieved_docs:
        for doc_group in retrieved_docs:
            for doc in doc_group:
                regulatory_context += doc + "\n"

    # ---------------------------------------------------
    # 📝 STEP 2: Build Prompt Template
    # ---------------------------------------------------

    template = """
You are a senior financial compliance analyst generating a Suspicious Activity Report (SAR).

Follow ALL regulatory and compliance requirements strictly.

===========================================================
REGULATORY GUIDANCE (Retrieved from Knowledge Base)
===========================================================
{regulatory_context}

===========================================================
CUSTOMER INFORMATION
===========================================================
Full Name: {full_name}
Date of Birth: {dob}
Address: {address}

===========================================================
ACCOUNT INFORMATION
===========================================================
Accounts: {accounts}

===========================================================
ACTIVITY DETAILS
===========================================================
Activity Start Date: {start_date}
Activity End Date: {end_date}
Total Suspicious Amount: ${amount}

Transactions:
{transactions}

===========================================================
TRIGGERED RULES
===========================================================
{rules}

===========================================================
MANDATORY REQUIREMENTS
===========================================================
1. Narrative must be >= 500 characters.
2. Must clearly answer WHO, WHAT, WHEN, WHERE, WHY, HOW.
3. Must describe investigation steps performed.
4. Must include specific transaction details.
5. Must include regulatory reference if structuring detected (e.g., 31 U.S.C. § 5324).
6. Use professional, objective language.
7. Do NOT use: guilty, criminal, definitely, certainly, obviously.
8. Include clear conclusion section.
9. End with confidence score statement.

Generate a complete, regulator-ready SAR narrative.
"""

    prompt = PromptTemplate(
        input_variables=[
            "regulatory_context",
            "full_name",
            "dob",
            "address",
            "accounts",
            "start_date",
            "end_date",
            "amount",
            "transactions",
            "rules",
        ],
        template=template,
    )

    # ---------------------------------------------------
    # 📦 STEP 3: Format Prompt
    # ---------------------------------------------------

    formatted_prompt = prompt.format(
        regulatory_context=regulatory_context,
        full_name=data["kyc"]["full_name"],
        dob=data["kyc"].get("date_of_birth", "Unknown"),
        address=data["kyc"].get("address", "Unknown"),
        accounts=data["accounts"],
        start_date=data["activity_start"],
        end_date=data["activity_end"],
        amount=f"{data['total_amount']:,.2f}",
        transactions=data["transactions"],
        rules=rule_result["triggered_rules"],
    )

    # ---------------------------------------------------
    # 🤖 STEP 4: Invoke LLM
    # ---------------------------------------------------

    response = llm.invoke(formatted_prompt)

    return formatted_prompt, response
