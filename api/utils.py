import os
import openai
import logging
from openai import OpenAI
from dotenv import load_dotenv
from .models import ReportCard
from course_content.models import UserContentAccess, Category, SubCategory, Lesson
# app.py
import re
import json
import time
from django.contrib.contenttypes.models import ContentType

load_dotenv()

logger = logging.getLogger(__name__)

EVALUATION_PROMPT = os.getenv('EVALUATION_PROMPT', "Welcome! Let's start chatting.")


# Initialize OpenAI Client
if "gpt" not in os.getenv("AI_MODEL"):
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("AI_BASE_URL"))
    logger.error("Using deepseek")
else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    logger.error("Using Open AI")

def get_ai_response(messages, temperature=1.3):
    """
    Generates AI responses using OpenAI's API.

    Args:
        messages (list): List of message objects for conversation context.
        temperature (float): Controls randomness. Higher = more creative responses.

    Returns:
        str: AI-generated response.
    """
    try:
        start=time.perf_counter()
        logger.error(f"CALLING AI ;;;;")
        logger.error(f"Received messages as => {messages=}")
        

        # Make API request
        # logger.warning(f"Got messages as => {messages=}")
        response = client.chat.completions.create(
            model=os.getenv("AI_MODEL"),
            messages=messages,
            temperature=temperature
        )

        # Extract AI response
        ai_message = response.choices[0].message.content
        logger.error(f"AI RESPONSE => {ai_message}")
        end=time.perf_counter()
        logger.error(f"AI RESPONSE TOOK {end-start} seconds")
        return ai_message

    except openai.OpenAIError as e:
        logger.error(f"Error communicating with OpenAI API: {e}")
        return "I'm sorry, I'm having trouble processing your request right now."
    except Exception as e:
        logger.exception("Error in AI response.")

        return "I'm sorry, I'm having trouble processing your request right now."


def evaluate_user_skills(user_messages):
    """
    Sends the user's messages to the AI for evaluation and returns the AI's response.
    """
    # logger.info(f"GOT USER MESSAGES AS {user_messages}")
    user_messages = [str(msg) for msg in user_messages]
    evaluation_prompt_formatted = EVALUATION_PROMPT.format(
        user_messages="\n".join(user_messages)
    )

    # logger.info(f"Evaluation prompt formatted {evaluation_prompt_formatted}")

    # Prepare messages for AI
    messages = [
        {"role": "system", "content": evaluation_prompt_formatted}
    ]

    # Get AI response
    ai_response = get_ai_response(messages)

    return ai_response




def parse_evaluation_result(evaluation_text):
    """
    Parses the AI's evaluation text and extracts scores and feedback.
    
    Parameters:
        evaluation_text (str): The textual evaluation response from the AI.
    
    Returns:
        dict: A dictionary containing extracted scores and feedback.
    """
    
    logger.info(f"EVALATION => {evaluation_text.strip('json').strip('`').strip().replace('json','')}")

    try:
        result = json.loads(evaluation_text.strip('json').strip('`').strip().replace('json',''))
        logger.info(f"RESULT {result}")
        # score = result.get('score')
        # feedback = result.get('feedback')
        # result = {"total_score": score, "feedback": feedback}

        # logger.info(f"==>RESULT {result}" )

        return result
    except Exception as e:
        logger.info(f"GOT ERROR EVALUATING {e}")

        # Initialize a dictionary to hold the results
        evaluation_data = {
            "engagement_score": None,
            "engagement_feedback": None,
            "humor_score": None,
            "humor_feedback": None,
            "empathy_score": None,
            "empathy_feedback": None,
            "total_score": None
        }

        # Define regex patterns for each score and explanation
        patterns = {
            "engagement": {
                "score": r"### \*\*Engagement Score:\s*(\d{1,3}(?:\.\d{1,2})?)/100\*\*",
                "feedback": r"### \*\*Engagement Score:.*?\*\*\n\*\*Explanation:\*\*\s*(.*?)\n---"
            },
            "humor": {
                "score": r"### \*\*Humor Score:\s*(\d{1,3}(?:\.\d{1,2})?)/100\*\*",
                "feedback": r"### \*\*Humor Score:.*?\*\*\n\*\*Explanation:\*\*\s*(.*?)\n---"
            },
            "empathy": {
                "score": r"### \*\*Empathy Score:\s*(\d{1,3}(?:\.\d{1,2})?)/100\*\*",
                "feedback": r"### \*\*Empathy Score:.*?\*\*\n\*\*Explanation:\*\*\s*(.*?)\n---"
            },
            "total": {
                "score": r"### \*\*Total Score:\s*(\d{1,3}(?:\.\d{1,2})?)/100\*\*",
                "feedback": None  # No feedback for total score
            }
        }

        # Iterate over each pattern and extract data
        for category, pattern in patterns.items():
            # Extract score
            score_match = re.search(pattern["score"], evaluation_text, re.DOTALL)
            if score_match:
                score = float(score_match.group(1))
                key = f"{category}_score"
                evaluation_data[key] = score
            else:
                logger.warning(f"Score for {category} not found in evaluation text.")

            # Extract feedback if applicable
            if pattern["feedback"]:
                feedback_match = re.search(pattern["feedback"], evaluation_text, re.DOTALL)
                if feedback_match:
                    feedback = feedback_match.group(1).strip()
                    key = f"{category}_feedback"
                    evaluation_data[key] = feedback
                else:
                    logger.warning(f"Feedback for {category} not found in evaluation text.")

    return evaluation_data




def process_evaluation(session, user_messages, ai_messages, session_id, user):
    """
    Build evaluation prompts, run evaluation logic, create and return a ReportCard.
    Then, unlock the corresponding category, subcategory, and lesson based on the
    lowest score (engagement, empathy, or humor).
    """
    # Build the prompt and evaluate
    prompt_to_send = [
        {"ai_message": ai, "user_message": user_msg} 
        for ai, user_msg in zip(ai_messages, user_messages)
    ]
    evaluation_result = evaluate_user_skills(prompt_to_send)
    evaluation_data = parse_evaluation_result(evaluation_result)
    
    feedback = evaluation_data.get("feedback", "Empty")
    engagement_score = int(evaluation_data.get("engagement_score", 0))
    empathy_score = int(evaluation_data.get("empathy_score", 0))
    humor_score = int(evaluation_data.get("humor_score", 0))
    total_score = (engagement_score + empathy_score + humor_score) // 3

    # Create the report card.
    report_card = ReportCard.objects.create(
        session=session,
        user=user,
        engagement_score=engagement_score,
        humor_score=humor_score,
        empathy_score=empathy_score,
        total_score=total_score,
        feedback=feedback
    )
    
    # Determine which score is the lowest.
    score_data = {
        "engagement": engagement_score,
        "empathy": empathy_score,
        "humor": humor_score
    }
    lowest_attribute = min(score_data, key=score_data.get)
    
    # Map the attribute to the corresponding Category name.
    attribute_to_category = {
        "engagement": "Engagement",
        "empathy": "Empathy",
        "humor": "Humor"
    }
    
    unlocked_category = None
    unlocked_subcategory = None
    unlocked_lesson = None
    
    # Unlock the target category
    try:
        category = Category.objects.get(name=attribute_to_category[lowest_attribute])
    except Category.DoesNotExist:
        category = None

    if category:
        ct_category = ContentType.objects.get_for_model(category)
        user_access, created = UserContentAccess.objects.get_or_create(
            user=user,
            content_type=ct_category,
            object_id=category.pk,
            defaults={'allowed': True}
        )
        if not created and not user_access.allowed:
            user_access.allowed = True
            user_access.save()
        unlocked_category = category

        # Unlock the first subcategory for this category, ordered by "order".
        subcategory = SubCategory.objects.filter(category=category).order_by("order").first()
        if subcategory:
            ct_subcategory = ContentType.objects.get_for_model(subcategory)
            user_access_sub, created = UserContentAccess.objects.get_or_create(
                user=user,
                content_type=ct_subcategory,
                object_id=subcategory.pk,
                defaults={'allowed': True}
            )
            if not created and not user_access_sub.allowed:
                user_access_sub.allowed = True
                user_access_sub.save()
            unlocked_subcategory = subcategory

            # Unlock the first lesson for this subcategory (assumes Lesson has a foreign key to SubCategory)
            lesson = Lesson.objects.filter(subcategory=subcategory).order_by("order").first()
            if lesson:
                ct_lesson = ContentType.objects.get_for_model(lesson)
                user_access_lesson, created = UserContentAccess.objects.get_or_create(
                    user=user,
                    content_type=ct_lesson,
                    object_id=lesson.pk,
                    defaults={'allowed': True}
                )
                if not created and not user_access_lesson.allowed:
                    user_access_lesson.allowed = True
                    user_access_lesson.save()
                unlocked_lesson = lesson

    return report_card, feedback, unlocked_category, unlocked_subcategory, unlocked_lesson

