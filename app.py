import os
import datetime

from braintrust import init_logger, traced, wrap_openai, invoke, current_span
from openai import OpenAI

logger = init_logger(project="SOAP-gen-demo")
client = wrap_openai(OpenAI(api_key=os.getenv("BRAINTRUST_API_KEY")))


example_transcript1 = """
Doctor: Hi, I'm Dr. Johnson. What brings you in today?

Patient: Hi. I've had this stomach pain since yesterday. It's getting worse.

Doctor: Okay—where exactly is the pain?

Patient: It started around my belly button but now it's moved down to the lower right side.

Doctor: Got it. Is it constant, or does it come and go?

Patient: It's pretty constant. Sharp, kind of stabbing when I move.

Doctor: Any nausea or vomiting?

Patient: Yeah, I felt sick to my stomach last night and I threw up once this morning.

Doctor: Have you had any fever?

Patient: Yeah, I felt hot earlier today. I don't know the exact temp.

Doctor: Any diarrhea or constipation?

Patient: No diarrhea. I haven't gone since yesterday, actually.

Doctor: How's your appetite?

Patient: I'm not hungry at all.

Doctor: Have you had anything like this before?

Patient: No, nothing like this.

Doctor: Any pain when you urinate or blood in the urine?

Patient: No, peeing's normal.

Doctor: Any chance you could have pulled a muscle or had a recent injury?

Patient: No, I haven't done anything like that.

Doctor: Alright. I'm going to examine your abdomen now. Let me know if it hurts when I press.

Doctor: Does it hurt here?

Patient: A little.

Doctor: And here on the lower right?

Patient: Yeah—ow, yeah, that really hurts.

Doctor: Okay. That's called rebound tenderness, which can be a sign of appendicitis. I'm also seeing guarding and pain with movement.

Patient: So it might be my appendix?

Doctor: Yes, that's my concern. We'll need to get some labs and imaging to confirm—probably a CT scan of your abdomen.

Patient: Okay.

Doctor: If it is appendicitis, you'll likely need surgery. But let's get the workup started so we know for sure.
"""

example_transcript2 = """
Doctor: Hi there! Good to see you both. What brings you in today?

Mother: Hi, thanks. He's had a sore throat since yesterday morning, and he woke up with a fever today. He says it hurts to swallow.

Doctor: Okay. Hey buddy, can you tell me what's been bothering you?

Child: My throat hurts. It hurts when I eat or drink.

Doctor: I'm sorry to hear that. Any belly pain or headache?

Child: My tummy hurts a little.

Mother: He was also saying his head hurt last night. And he hasn't wanted to eat much today.

Doctor: Got it. Has he had any cough, runny nose, or sneezing?

Mother: No, that's the thing—it's just the sore throat and the fever.

Doctor: Any nausea, vomiting, or rash?

Mother: No vomiting. No rash that I've noticed.

Doctor: Has he been exposed to anyone with strep recently?

Mother: Yes, actually. There's been a few kids in his class out sick, and one of them had strep.

Doctor: That's helpful to know. What's his temperature been at home?

Mother: It was 101.5 this morning.

Doctor: Okay. I'll take a look and do a quick strep test. Sound good?

Doctor: Alright, open up big for me... say "ahhh"... I'm just going to swab the back of your throat really quickly. There you go—good job!

Mother: He did better than I thought he would!

Doctor: He was great. I'll run this test and be right back.

Doctor: Okay, the rapid strep test came back positive, so it looks like he does have strep throat.

Mother: Okay. What do we need to do?

Doctor: We'll start him on an antibiotic—probably amoxicillin or penicillin. It should help him feel better within a day or two. He'll need to stay home from school for at least 24 hours after starting the medication and until the fever's gone.

Mother: Got it.

Doctor: You can give Tylenol or ibuprofen for the fever and pain. Encourage fluids and soft foods. If symptoms get worse or if he develops a rash, call us right away.

Mother: Okay, thank you.

Doctor: You're welcome! I'll send the prescription to your pharmacy now.

Child: Do I have to take medicine?

Doctor: Just for a little while, but it'll help your throat feel better fast.
"""

example_transcript3 = """
Doctor: Good morning. How are you doing today?

Patient: Morning, doc. Eh, I've been better. That's why I'm here.

Doctor: Okay, tell me what's been going on.

Patient: Well, I've just been feeling tired all the time. It's been going on for a few months now. I thought it might just be getting older, but I'm dragging no matter how much I sleep.

Doctor: Got it. Any other symptoms you've noticed?

Patient: Yeah, actually—I've been getting really thirsty. Like constantly. I keep a bottle of water with me everywhere. And I've been peeing a lot more too, even waking up twice a night.

Doctor: Increased thirst and urination—okay. How about your vision? Any changes?

Patient: Funny you ask—I've noticed my vision's gotten a little blurry lately, especially in the afternoons. I thought maybe I needed a new prescription.

Doctor: That's helpful. Any recent changes in weight?

Patient: I lost about 10 pounds, but I wasn't trying to. I thought it was just from cutting back on snacks.

Doctor: Okay. How's your appetite?

Patient: About the same, maybe even more hungry than usual.

Doctor: Any numbness or tingling in your feet?

Patient: Now that you mention it, yes. I get this weird tingling in my toes, mostly in the evenings when I sit down.

Doctor: Understood. How's your medical history? Any known high blood pressure, cholesterol, anything like that?

Patient: Yeah, I've had high blood pressure for a few years. I take lisinopril. I think my cholesterol's been borderline, but I'm not on meds for that.

Doctor: Any family history of diabetes?

Patient: My dad had it. I think he was diagnosed in his 60s too.

Doctor: Alright. Have you ever had your blood sugar checked?

Patient: Not that I can remember. Maybe once at a health fair, years ago.

Doctor: Okay. Based on what you're describing—fatigue, increased thirst and urination, unintended weight loss, blurred vision, and tingling in the feet—I'm concerned about high blood sugar. We'll check your glucose and A1c today and see where things stand.

Patient: Okay. I figured something was off.

Doctor: We'll get you some answers. If it is diabetes, we'll talk about a treatment plan and how to manage it.

Patient: Sounds good. Thanks, doc.
"""

# Using Invoke to generate a SOAP note from a transcript & log to Braintrust
@traced
def generate_soap_note(transcript: str) -> tuple[str, str]:
    result = invoke(
        project_name="SOAP-gen-demo",
        slug="system1-1463",
        input=transcript,
    )
    span = current_span()
    exported = span.export()
    return result, exported
    
def fake_feedback_handler(request_id, score, comment, user_id):
    with logger.start_span(parent=request_id) as span:
        span.set_attributes("correctness", "score")
        metadata = {
            "user_id": user_id,
            "feedback_type": "manual",
            "timestamp": str(datetime.datetime.now())
        }
        print("Logging feedback with metadata:", metadata)
        logger.log_feedback(
            id=span.id,
            scores={
                "correctness": score,
            },
            comment=comment,
            metadata=metadata,
        )

# Generate a SOAP note
result, real_request_id = generate_soap_note(example_transcript1)

# Simulate user feedback
fake_feedback_handler(
    request_id=real_request_id, 
    score=1,  # Fake score
    comment="This is a fake feedback comment.",  # Fake comment
    user_id="user_456"  # Fake user ID
)

print(result)

"""
# Using Traced to generate a SOAP note from a transcript & log to Braintrust
@traced
def generate_soap_note_traced(transcript: str) -> str:
    span = current_span()
    exported = span.export()

    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": transcript},
        ],
    )
"""