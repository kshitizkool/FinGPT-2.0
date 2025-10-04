import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

logger = logging.getLogger(__name__)

# Ensure environment variables from .env are loaded when this module is imported
load_dotenv()

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, config: Dict, agent_name: str):
        self.config = config
        self.agent_name = agent_name
        self.agent_config = config["agents"].get(agent_name, {})
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Initialize chat history
        self.chat_history = ChatMessageHistory()
        
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LLM with configuration"""
        llm_config = self.config["llm"]
        
        return ChatOpenAI(
            model=llm_config["model"],
            api_key=llm_config["api_key"],
            base_url="https://openrouter.ai/api/v1",
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4000),
            timeout=llm_config.get("timeout", 60)
        )
    
    @abstractmethod
    def process(self, state: Dict) -> Dict:
        """Process the input state and return updated state"""
        pass
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        return self.agent_config.get("system_prompt", "You are a helpful assistant.")
    
    def log_action(self, action: str, details: Dict = None):
        """Log agent actions for observability"""
        logger.info(f"Agent {self.agent_name}: {action}", extra={"details": details})

class Agent:
    """A simple AI agent that can solve tasks through multi-step reasoning"""

    def __init__(self, model="x-ai/grok-4-fast:free"):
        """
        Initialize the agent with the specified model

        Args:
            model (str): The OpenRouter model identifier to use
        """
        self.model = model
        self.client = self._setup_client()
        self.conversation_history = []  # FIXME: Not actually using this yet
        # self.max_retries = 3  # Might need this for production

    def _setup_client(self):
        """Set up the OpenRouter client"""
        # Prefer explicit OPENROUTER_API_KEY, fall back to a generic API_KEY for compatibility
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")

        if not api_key:
            raise ValueError(
                "OpenRouter API key not found. Please set the OPENROUTER_API_KEY "
                "environment variable in your .env file (or API_KEY as a fallback)."
            )

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": os.getenv("YOUR_SITE_URL", "http://localhost:5000"),
                "X-Title": os.getenv("YOUR_SITE_NAME", "Agentic AI Demo")
            }
        )

        return client

    def _call_llm(self, messages):
        """
        Make an API call to the language model

        Args:
            messages (list): List of message objects for the conversation

        Returns:
            str: The model's response content
        """
        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Maybe we should retry here?
            return None

    def analyze_task(self, user_query):
        """
        Break down a user query into discrete steps

        Args:
            user_query (str): The user's request

        Returns:
            list: List of steps to solve the task
        """
        system_prompt = """
        You are an AI task planner. Your job is to break down a user's request 
        into a series of clear, discrete steps that can be executed sequentially.

        Respond with a JSON array of steps, where each step has:
        1. A "description" field describing what needs to be done
        2. A "reasoning" field explaining why this step is necessary

        Format your response as a valid JSON array without any additional text.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Break down this task into steps: {user_query}"}
        ]

        response = self._call_llm(messages)

        try:
            # Extract the JSON array from the response
            steps = json.loads(response)
            return steps
        except json.JSONDecodeError:
            print("Error: Could not parse response as JSON")
            print(f"Raw response: {response}")
            return []

    def execute_step(self, step, context):
        """
        Execute a single step in the plan

        Args:
            step (dict): The step to execute
            context (str): Context from previous steps

        Returns:
            str: Result of executing the step
        """
        system_prompt = """
        You are an AI assistant focusing on executing a specific task step.
        Use the provided context and step description to complete this specific step only.
        Your response should be detailed and directly address the step's requirements.
        """

        step_msg = f"Context so far: {context}\n\nExecute this step: {step['description']}\n\nReasoning: {step['reasoning']}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": step_msg}
        ]

        return self._call_llm(messages)

    def compile_results(self, steps_results, user_query):
        """
        Compile the results of all steps into a final response

        Args:
            steps_results (list): Results from each executed step
            user_query (str): The original user query

        Returns:
            str: Final compiled response
        """
        system_prompt = """
        You are an AI assistant that compiles information from multiple processing steps 
        into a coherent, unified response. Your goal is to present the information clearly 
        and directly address the user's original query.
        """

        # Join step results - could probably be a one-liner but this is clearer
        step_texts = []
        for i, res in enumerate(steps_results):
            step_num = i + 1
            step_texts.append(f"Step {step_num} result: {res}")
        steps_text = "\n\n".join(step_texts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original query: {user_query}\n\nResults from steps:\n{steps_text}\n\nPlease provide a comprehensive, unified response to the original query."}
        ]

        return self._call_llm(messages)

    def solve(self, user_query):
        """
        Solve a task through multi-step reasoning

        Args:
            user_query (str): The user's request

        Returns:
            dict: A dictionary containing the original query, steps taken, 
                  results of each step, and the final response
        """
        print(f"🤔 Analyzing task: {user_query}")
        steps = self.analyze_task(user_query)

        if not steps:
            return {"error": "Could not break down the task into steps"}

        print(f"📋 Breaking down into {len(steps)} steps:")
        for i, step in enumerate(steps):
            print(f"  {i+1}. {step['description']}")

        step_results = []  # Going with snake_case here, inconsistent with camelCase elsewhere
        context = ""

        for i, step in enumerate(steps):
            print(f"\n⚙️ Executing step {i+1}: {step['description']}")
            result = self.execute_step(step, context)
            step_results.append(result)
            context += f"\nStep {i+1} result: {result}"
            print(f"  ✅ Completed")
            # Add a small delay to avoid rate limits
            time.sleep(1)  # Maybe this should be configurable?

        print("\n🔄 Compiling final response...")
        final_response = self.compile_results(step_results, user_query)

        return {
            "query": user_query,
            "steps": steps,
            "step_results": step_results,  # Note: variable name changed from steps_results
            "final_response": final_response
        }

def main():
    """Main function to demonstrate the agent's capabilities"""
    # Initialize the agent with a capable model
    main()