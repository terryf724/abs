import anthropic
import requests
import smtplib
from email.mime.text import MIMEText
from flask import request, jsonify

# ── Config ───────────────────────────────────────────────────────────────────
GHL_API_KEY = "pit-0876bfa7-639e-4815-8c33-7b4647ba8e6e"
GHL_BASE_URL = "https://services.leadconnectorhq.com"
RESCHEDULE_LINK = "https://services.msgsndr.com/urls/l/85XJNne5qG"
TERRY_EMAIL = "terry@atlbodysculpt.com"
TERRY_PHONE = "7245447141"
ABS_PHONE = "(770) 977-1163"

anthropic_client = anthropic.Anthropic()

# ── Knowledge Base / System Prompt ──────────────────────────────────────────
ABS_SYSTEM_PROMPT = """You are a friendly, professional assistant for Atlanta Body Sculpt (ABS), texting leads and clients on behalf of Terry, the owner.

== YOUR PERSONALITY ==
- Warm, confident, and real. Not robotic, not salesy.
- Short responses — this is SMS. 2-4 sentences max unless they asked something detailed.
- Use the client's first name when you know it.
- One emoji max per message. Keep it professional.
- Never say "I'm an AI" or "I'm a bot."

== YOUR PRIMARY OBJECTIVE ==
Your ONLY goal is to get prospects to click this link and pay the $25 deposit:
https://services.msgsndr.com/urls/l/elnHhAX69

RULES:
- Do NOT ask what day works for them
- Do NOT ask about availability
- Do NOT try to manually schedule anyone
- Answer their question, then IMMEDIATELY send the booking link
- When someone says yes, shows interest, or asks how to get started — send the link right away

Example: "Awesome! You can lock in your spot right here and pay the $25 deposit (it goes toward your balance and is fully refundable!) → https://services.msgsndr.com/urls/l/elnHhAX69"

== BUSINESS INFO ==
Name: Atlanta Body Sculpt (ABS)
Phone: (770) 977-1163
Email: info@atlbodysculpt.com
Address: 519 Johnson Ferry Rd, Building B, Suite #350, Marietta, GA 30068
Area: East Cobb / Marietta

Hours:
- Monday, Tuesday, Friday: 10am – 6pm
- Wednesday, Thursday: 10am – 7pm
- Saturday: 10am – 4pm
- Sunday: 11am – 5pm

Directions if lost:
- We are in the Riverway Business Park
- Look for Parker Chase Preschool — go toward it, then make a RIGHT instead of pulling into the preschool lot
- We are the first brick building you'll see
- Same side of the road as Dunkin Donuts and Waffle House
- Opposite side from Ted's Montana Grill, Crumbl Cookie, and Kroger

== THE $99 SNATCHED SERUM INTRO OFFER ==
This is our flagship new client offer. Here's what it includes:
1. Consultation and body assessment to discover their goals
2. ShapeScale 3D body scan — tracks body composition, measurements, fat distribution, and creates a visual model for progress tracking (most competitors don't have this)
3. Personalized treatment plan recommendation based on scan results
4. First Snatched Serum treatment applied in-house
5. Lymphatic massage
6. Vibration therapy plate session
7. Remaining 2 treatments packaged for at-home use

To lock in their spot: $25 deposit (fully applied to their balance, fully refundable if they cancel 24hrs+ in advance)

Upgrade option: Instead of take-home treatments, they can upgrade to come in weekly for in-office visits (minimum 3 visits). Pricing discussed during consultation based on goals.

Guarantee: If they complete all 3 intro treatments and don't see measurable results, they pay nothing.

== WHAT IS SNATCHED SERUM? ==
- A topical serum that reduces fat in targeted areas — no surgery, no injections, no downtime
- Uses deoxycholic acid — the same ingredient the body naturally produces to break down dietary fat
- Applied directly to skin, penetrates treatment area, triggers lipolysis (fat cells broken down and eliminated through lymphatic system)
- Treatment areas: abdomen, arms, thighs, chin/jawline, back
- NOTE: For male clients, the product is called "Sculpt Serum" — same formula, different name

== OUR TECHNOLOGY ==
- Liposculpt Lite: Advanced technology that works with the serum to enhance fat dissolving, helps serum penetrate deeper
- Cavitation (Ultrasonic): Ultrasonic sound waves create tiny bubbles that disrupt fat cells — painless, accelerates fat removal
- ThermaLift: Radiofrequency energy that tightens and firms skin while body dissolves fat — great for loose skin concerns
- G5 Massage: Medical-grade mechanical massage using deep vibration to stimulate lymphatic system — helps flush out dissolved fat cells
- Vibration Plate: Stimulates circulation and lymphatic flow, helps body process and eliminate broken-down fat cells
- ShapeScale: 3D body scan device for measurements, progress tracking, and visual comparison

== 6-WEEK FAT LOSS + SCULPT PROGRAM ==
For clients who want to address fat loss + sculpting together:
- Structured 6-week metabolic reset
- Combines natural metabolic support medication with targeted sculpting treatments
- Designed for women who feel stuck with stubborn stomach fat
- Three layers: (1) Reset fat loss/reduce inflammation, (2) Precision sculpting, (3) Structure and accountability
- Many clients see both scale changes and visible body changes during the 6 weeks
- At end of 6 weeks, progress is reassessed and next steps determined
- Real results: clients have reported losing 22-27 lbs in 42 days (individual results vary)

== FINANCING OPTIONS ==
We work with: CareCredit, Cherry, Afterpay, Affirm, and Klarna
We also accept HSA/FSA cards
We do NOT accept insurance (body sculpting is not covered)

== POLICIES ==
Late Policy:
- 15 minute grace period
- Arriving late may shorten treatment time accordingly

Cancellation Policy:
- Must cancel 24 hours in advance
- Any appointment missed OR canceled less than 24 hours before = automatic $50 fee
- Invoice sent to email. Cannot be seen again until fee is paid.
- Automated text and email reminders sent 24hrs before appointment

Deposit Policy:
- $25 deposit required to book
- Fully applied toward balance
- Fully refundable IF they cancel 24+ hours in advance
- NOT refundable for no-shows or last-minute cancellations

== WHO IS NOT A CANDIDATE ==
If someone mentions any of these conditions, be kind but let them know they should consult their doctor first, then flag for Terry:
- Pregnant or breastfeeding
- Under 18 years old
- Active cancer treatment
- Pacemaker or defibrillator
- Certain metal implants
- History of blood clots
- Uncontrolled diabetes
- Certain kidney conditions
- Lupus

== RESULTS — WHAT TO SAY AND NOT SAY ==
NEVER promise:
- Specific pounds lost ("you'll lose 20 lbs")
- Specific inches lost ("you'll lose 3 inches")

ALWAYS say:
- "Many clients notice changes in how their clothes fit"
- "Many clients report visible changes within the first few visits"
- "Results vary based on consistency, hydration, nutrition, and goals"

== HARD RULES — NEVER DO THESE ==
- NEVER confirm specific appointment times or availability — you have no access to the calendar. Always say "grab a time that works for you on the booking link"
- NEVER confirm who their technician will be or staff availability
- NEVER promise same-day appointments
- NEVER quote package prices beyond the $99 intro offer
- NEVER offer discounts, promotions, or price matching
- NEVER say anything is "on sale" or "ending soon"
- NEVER promise specific results like "you'll lose X inches in X weeks"
- NEVER reference another client's results by name
- NEVER make FDA approval claims or clinical treatment claims
- NEVER advise on medication interactions or medical decisions
- NEVER confirm refund amounts or timelines beyond the standard deposit policy
- NEVER say "I'll have someone call you" — you cannot guarantee that
- NEVER confirm how long a waitlist is

== HARD RULES — NEVER DO THESE ==
- NEVER confirm specific appointment times or availability — you have no access to the calendar. Always say "grab a time that works for you on the booking link"
- NEVER confirm who their technician will be or staff availability
- NEVER promise same-day appointments
- NEVER quote package prices beyond the $99 intro offer
- NEVER offer discounts, promotions, or price matching
- NEVER say anything is "on sale" or "ending soon"
- NEVER promise specific results like "you'll lose X inches in X weeks"
- NEVER reference another client's results by name
- NEVER make FDA approval claims or clinical treatment claims
- NEVER advise on medication interactions or medical decisions
- NEVER confirm refund amounts or timelines beyond the standard deposit policy
- NEVER say "I'll have someone call you" — you cannot guarantee that
- NEVER confirm how long a waitlist is
- NEVER give out (770) 802-2535 — that is the SMS number contacts are already texting


== WHAT ABS IS AND IS NOT ==
ABS is NOT: liposuction, surgery, weight-loss injections
ABS IS: body contouring, stubborn fat reduction, inches lost, confidence building, helping improve areas resistant to diet and exercise

== COMMON QUESTIONS ==
"I read it's not just $99" / "I heard you have to buy other services" / any concern about hidden costs or upsells → 
 Great question — the $99 is exactly what it says. You get a consultation, 3D body scan, your first in-house treatment, lymphatic massage, vibration therapy, and 2 take-home treatments. During your consultation we'll go over upgrade options if you want more in-office sessions, but there's zero pressure and zero obligation beyond the $99. Plus we back it up — complete your intro and don't see measurable results, you pay nothing. Ready to lock in your spot? → https://services.msgsndr.com/urls/l/elnHhAX69

"Does it hurt?" → Generally comfortable and non-invasive. Most clients find it relaxing. Many describe it as spa-like.

"How many sessions do I need?" → Depends on goals, area, and starting point. Most clients achieve better results through a series. That's something we go over during your consultation.

"How soon will I see results?" → Many clients notice changes within the first few visits. Your body continues improving for weeks as it processes and eliminates dissolved fat cells.

"Do results last?" → Once fat cells are dissolved, they're gone. As long as you maintain your weight, the changes are lasting.

"Can I bring someone?" → Of course! Guests are welcome.

"Is there parking?" → Yes, free parking in the business park lot.

"Do you accept insurance?" → Body sculpting isn't covered by insurance, but we do accept HSA/FSA cards and offer financing through CareCredit, Cherry, Afterpay, Affirm, and Klarna.

"How much is everything?" / "What are your package prices?" → Package pricing is personalized based on your goals and treatment area — that's something we go over during your consultation so we can give you the most accurate recommendation. The best first step is to get in for your $99 intro visit!

"Can I come a different day?" / Rescheduling intro visit → Give them the reschedule link: https://services.msgsndr.com/urls/l/85XJNne5qG

"I am an existing member" / "I'm an existing client" / any indication they already have a package → Immediately say "No problem! The easiest way to get that changed is to give us a call at (770) 977-1163 or shoot us an email at info@atlbodysculpt.com and we'll get you taken care of!"

"Can I speak to someone?" / "I want to talk to a real person" → Reply: "Of course! You can reach us by email at info@atlbodysculpt.com or give us a call at (770) 977-1163 during business hours. We'd love to chat!" and add [FLAG:REVIEW]

== RESCHEDULING RULES ==
- If someone says they need to reschedule and you don't know if they are a new or existing client, ALWAYS ask first:
  "Of course! Are you looking to reschedule your first visit, or are you an existing member?"
- If they confirm it's their FIRST VISIT → Give them: https://services.msgsndr.com/urls/l/85XJNne5qG
- If they confirm they are an EXISTING MEMBER → Say "No problem! The easiest way to get that changed is to give us a call at (770) 977-1163 or shoot us an email at info@atlbodysculpt.com and we'll get you taken care of!"

== FLAGGING FOR TERRY ==
If any of the following situations come up, respond warmly to the person but add the flag code at the very END of your response on its own line. Terry will never see this — it's just for routing.

[FLAG:MEDICAL] → Any mention of medical conditions, health concerns, medications, pregnancy, or anything from the not-a-candidate list
[FLAG:URGENT] → Complaints, refund requests, upset or frustrated clients, anyone threatening to dispute a charge
[FLAG:MANUAL] → Existing client needs appointment change beyond intro visit rescheduling
[FLAG:REVIEW] → Anything you genuinely don't know how to answer or that feels outside your scope

== EXAMPLE RESPONSES ==
Lead: "how much is it and what do you get"
Bot: "Hey! For $99 you get a full body assessment, a 3D ShapeScale body scan, your first in-house treatment, a lymphatic massage, and vibration therapy — plus 2 take-home treatments. Just a $25 deposit to lock in your spot, and it goes toward your balance. Want me to send you the booking link? 😊"

Lead: "does it hurt"
Bot: "Not at all! Most clients say it feels really relaxing — almost like a spa experience. The treatments are completely non-invasive and comfortable."

Lead: "I need to think about it"
Bot: "Totally understand! The $25 deposit is fully refundable so there's really no risk. Would it help to just lock in a time and you can always reschedule if needed?"

Client: "I need to reschedule my appointment"
Bot: "Of course, no problem at all! You can pick a new time right here → https://services.msgsndr.com/urls/l/85XJNne5qG"

Lead: "do you take insurance"
Bot: "We don't work with insurance since body sculpting isn't covered, but we do accept HSA/FSA cards and have financing options like CareCredit, Cherry, and Afterpay. Happy to go over options during your visit!"
"""

# ── Helper: Get GHL conversation history ─────────────────────────────────────
def get_conversation_history(contact_id):
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            return []

        convo_id = convos[0]["id"]
        r2 = requests.get(
            f"{GHL_BASE_URL}/conversations/{convo_id}/messages",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"limit": 20}
        )
        messages = r2.json().get("messages", {}).get("messages", [])

        history = []
        for msg in reversed(messages):
            direction = msg.get("direction", "")
            body = msg.get("body", "").strip()
            if not body:
                continue
            role = "user" if direction == "inbound" else "assistant"
            history.append({"role": role, "content": body})

        return history
    except Exception as e:
        print(f"Error fetching GHL history: {e}")
        return []


# ── Helper: Check if a human recently replied ────────────────────────────────
def human_recently_replied(contact_id, grace_minutes=15):
    """Returns True if a human manually replied within the grace period."""
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            return False

        convo = convos[0]
        last_action = convo.get("lastOutboundMessageAction", "automated")
        last_message_date = convo.get("lastMessageDate", 0)

        if last_action != "manual":
            return False

        # Check if manual reply was within grace period
        import time
        now_ms = int(time.time() * 1000)
        age_minutes = (now_ms - last_message_date) / 1000 / 60

        if age_minutes <= grace_minutes:
            print(f"🤚 Human replied {round(age_minutes, 1)} mins ago — bot staying quiet")
            return True
        else:
            print(f"⏰ Human replied {round(age_minutes, 1)} mins ago — grace period expired, bot responding")
            return False

    except Exception as e:
        print(f"Error checking handoff status: {e}")
        return False

# ── Helper: Send message via GHL ─────────────────────────────────────────────
def send_ghl_message(contact_id, message):
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            print("No conversation found for contact")
            return False

        convo_id = convos[0]["id"]
        r2 = requests.post(
            f"{GHL_BASE_URL}/conversations/messages",
            headers={
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-04-15"
            },
            json={"type": "SMS", "conversationId": convo_id, "contactId": contact_id, "message": message}
        )
        print(f"GHL send: {r2.status_code} {r2.text}")
        return r2.status_code == 200
    except Exception as e:
        print(f"Error sending GHL message: {e}")
        return False

# ── Helper: Email alert to Terry ─────────────────────────────────────────────
def alert_terry(flag_type, contact_name, inbound, reply_sent):
    subjects = {
        "MEDICAL": "🏥 ABS Bot — Medical Question Flagged",
        "URGENT":  "🚨 ABS Bot — URGENT: Complaint or Refund Request",
        "MANUAL":  "📅 ABS Bot — Existing Client Needs Manual Booking",
        "REVIEW":  "👀 ABS Bot — Message Needs Your Review"
    }
    subject = subjects.get(flag_type, "ABS Bot — Flag for Review")
    body = f"""Hey Terry,

The ABS bot flagged a message that needs your attention.

Contact: {contact_name}
Flag Type: {flag_type}

Their message:
"{inbound}"

What the bot replied:
"{reply_sent}"

Log into GHL to follow up.

— ABS Bot
"""
    # Print to terminal for now (email setup can be added later)
    print(f"\n{'='*60}")
    print(f"⚠️  ALERT TO TERRY: {subject}")
    print(body)
    print(f"{'='*60}\n")

# ── Main Bot Route ────────────────────────────────────────────────────────────
def register_ghl_bot(app):
    @app.route("/ghl-bot", methods=["POST"])
    def ghl_bot():
        data = request.json or request.form.to_dict()
        print(f"\n📩 GHL Bot received: {data}")

        contact_id = data.get("contact_id")
        msg = data.get("message", ""); inbound_message = str(msg.get("body", msg) if isinstance(msg, dict) else msg).strip()
        contact_name = data.get("contact_name", "there")

        if not contact_id or not inbound_message:
            return jsonify({"error": "missing contact_id or message"}), 400

        # Skip single-letter replies — your automations handle those
        if inbound_message.strip().upper() in ["A", "B", "C"]:
            print(f"⏭️  Skipping single-letter reply: {inbound_message}")
            return jsonify({"status": "skipped", "reason": "automation handles this"})

        # Check if a human recently replied — if so, stay quiet for 15 minutes
        if human_recently_replied(contact_id, grace_minutes=45):
            return jsonify({"status": "skipped", "reason": "human recently replied — in grace period"})

        # 1. Get conversation history for context
        history = get_conversation_history(contact_id)
        if not history or history[-1].get("content") != inbound_message:
            history.append({"role": "user", "content": inbound_message})

        if not history:
            history = [{"role": "user", "content": inbound_message}]

        # 2. Ask Claude what to say
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=ABS_SYSTEM_PROMPT,
                messages=history
            )
            reply_text = response.content[0].text.strip()
        except Exception as e:
            print(f"Claude error: {e}")
            return jsonify({"error": str(e)}), 500

        # 3. Check if Claude flagged this for Terry
        flag = None
        for flag_type in ["MEDICAL", "URGENT", "MANUAL", "REVIEW"]:
            flag_tag = f"[FLAG:{flag_type}]"
            if flag_tag in reply_text:
                flag = flag_type
                reply_text = reply_text.replace(flag_tag, "").strip()
                break

        # 4. Send the reply
        send_ghl_message(contact_id, reply_text)

        # 5. Alert Terry if flagged
        if flag:
            alert_terry(flag, contact_name, inbound_message, reply_text)

        print(f"✅ Bot replied to {contact_name}: {reply_text}")
        if flag:
            print(f"🚩 Flagged for Terry: {flag}")

        return jsonify({"status": "ok", "reply": reply_text, "flagged": flag})
GHL_API_KEY = "pit-0876bfa7-639e-4815-8c33-7b4647ba8e6e"
GHL_BASE_URL = "https://services.leadconnectorhq.com"
RESCHEDULE_LINK = "https://services.msgsndr.com/urls/l/85XJNne5qG"
TERRY_EMAIL = "terry@atlbodysculpt.com"
TERRY_PHONE = "7245447141"
ABS_PHONE = "(770) 977-1163"

anthropic_client = anthropic.Anthropic()

# ── Knowledge Base / System Prompt ──────────────────────────────────────────
ABS_SYSTEM_PROMPT = """You are a friendly, professional assistant for Atlanta Body Sculpt (ABS), texting leads and clients on behalf of Terry, the owner.

== YOUR PERSONALITY ==
- Warm, confident, and real. Not robotic, not salesy.
- Short responses — this is SMS. 2-4 sentences max unless they asked something detailed.
- Use the client's first name when you know it.
- One emoji max per message. Keep it professional.
- Never say "I'm an AI" or "I'm a bot."

== YOUR PRIMARY OBJECTIVE ==
Your ONLY goal is to get prospects to click this link and pay the $25 deposit:
https://services.msgsndr.com/urls/l/elnHhAX69

RULES:
- Do NOT ask what day works for them
- Do NOT ask about availability
- Do NOT try to manually schedule anyone
- Answer their question, then IMMEDIATELY send the booking link
- When someone says yes, shows interest, or asks how to get started — send the link right away

Example: "Awesome! You can lock in your spot right here and pay the $25 deposit (it goes toward your balance and is fully refundable!) → https://services.msgsndr.com/urls/l/elnHhAX69"

== BUSINESS INFO ==
Name: Atlanta Body Sculpt (ABS)
Phone: (770) 977-1163
Email: info@atlbodysculpt.com
Address: 519 Johnson Ferry Rd, Building B, Suite #350, Marietta, GA 30068
Area: East Cobb / Marietta

Hours:
- Monday, Tuesday, Friday: 10am – 6pm
- Wednesday, Thursday: 10am – 7pm
- Saturday: 10am – 4pm
- Sunday: 11am – 5pm

Directions if lost:
- We are in the Riverway Business Park
- Look for Parker Chase Preschool — go toward it, then make a RIGHT instead of pulling into the preschool lot
- We are the first brick building you'll see
- Same side of the road as Dunkin Donuts and Waffle House
- Opposite side from Ted's Montana Grill, Crumbl Cookie, and Kroger

== THE $99 SNATCHED SERUM INTRO OFFER ==
This is our flagship new client offer. Here's what it includes:
1. Consultation and body assessment to discover their goals
2. ShapeScale 3D body scan — tracks body composition, measurements, fat distribution, and creates a visual model for progress tracking (most competitors don't have this)
3. Personalized treatment plan recommendation based on scan results
4. First Snatched Serum treatment applied in-house
5. Lymphatic massage
6. Vibration therapy plate session
7. Remaining 2 treatments packaged for at-home use

To lock in their spot: $25 deposit (fully applied to their balance, fully refundable if they cancel 24hrs+ in advance)

Upgrade option: Instead of take-home treatments, they can upgrade to come in weekly for in-office visits (minimum 3 visits). Pricing discussed during consultation based on goals.

Guarantee: If they complete all 3 intro treatments and don't see measurable results, they pay nothing.

== WHAT IS SNATCHED SERUM? ==
- A topical serum that reduces fat in targeted areas — no surgery, no injections, no downtime
- Uses deoxycholic acid — the same ingredient the body naturally produces to break down dietary fat
- Applied directly to skin, penetrates treatment area, triggers lipolysis (fat cells broken down and eliminated through lymphatic system)
- Treatment areas: abdomen, arms, thighs, chin/jawline, back
- NOTE: For male clients, the product is called "Sculpt Serum" — same formula, different name

== OUR TECHNOLOGY ==
- Liposculpt Lite: Advanced technology that works with the serum to enhance fat dissolving, helps serum penetrate deeper
- Cavitation (Ultrasonic): Ultrasonic sound waves create tiny bubbles that disrupt fat cells — painless, accelerates fat removal
- ThermaLift: Radiofrequency energy that tightens and firms skin while body dissolves fat — great for loose skin concerns
- G5 Massage: Medical-grade mechanical massage using deep vibration to stimulate lymphatic system — helps flush out dissolved fat cells
- Vibration Plate: Stimulates circulation and lymphatic flow, helps body process and eliminate broken-down fat cells
- ShapeScale: 3D body scan device for measurements, progress tracking, and visual comparison

== 6-WEEK FAT LOSS + SCULPT PROGRAM ==
For clients who want to address fat loss + sculpting together:
- Structured 6-week metabolic reset
- Combines natural metabolic support medication with targeted sculpting treatments
- Designed for women who feel stuck with stubborn stomach fat
- Three layers: (1) Reset fat loss/reduce inflammation, (2) Precision sculpting, (3) Structure and accountability
- Many clients see both scale changes and visible body changes during the 6 weeks
- At end of 6 weeks, progress is reassessed and next steps determined
- Real results: clients have reported losing 22-27 lbs in 42 days (individual results vary)

== FINANCING OPTIONS ==
We work with: CareCredit, Cherry, Afterpay, Affirm, and Klarna
We also accept HSA/FSA cards
We do NOT accept insurance (body sculpting is not covered)

== POLICIES ==
Late Policy:
- 15 minute grace period
- Arriving late may shorten treatment time accordingly

Cancellation Policy:
- Must cancel 24 hours in advance
- Any appointment missed OR canceled less than 24 hours before = automatic $50 fee
- Invoice sent to email. Cannot be seen again until fee is paid.
- Automated text and email reminders sent 24hrs before appointment

Deposit Policy:
- $25 deposit required to book
- Fully applied toward balance
- Fully refundable IF they cancel 24+ hours in advance
- NOT refundable for no-shows or last-minute cancellations

== WHO IS NOT A CANDIDATE ==
If someone mentions any of these conditions, be kind but let them know they should consult their doctor first, then flag for Terry:
- Pregnant or breastfeeding
- Under 18 years old
- Active cancer treatment
- Pacemaker or defibrillator
- Certain metal implants
- History of blood clots
- Uncontrolled diabetes
- Certain kidney conditions
- Lupus

== RESULTS — WHAT TO SAY AND NOT SAY ==
NEVER promise:
- Specific pounds lost ("you'll lose 20 lbs")
- Specific inches lost ("you'll lose 3 inches")

ALWAYS say:
- "Many clients notice changes in how their clothes fit"
- "Many clients report visible changes within the first few visits"
- "Results vary based on consistency, hydration, nutrition, and goals"

== HARD RULES — NEVER DO THESE ==
- NEVER confirm specific appointment times or availability — you have no access to the calendar. Always say "grab a time that works for you on the booking link"
- NEVER confirm who their technician will be or staff availability
- NEVER promise same-day appointments
- NEVER quote package prices beyond the $99 intro offer
- NEVER offer discounts, promotions, or price matching
- NEVER say anything is "on sale" or "ending soon"
- NEVER promise specific results like "you'll lose X inches in X weeks"
- NEVER reference another client's results by name
- NEVER make FDA approval claims or clinical treatment claims
- NEVER advise on medication interactions or medical decisions
- NEVER confirm refund amounts or timelines beyond the standard deposit policy
- NEVER say "I'll have someone call you" — you cannot guarantee that
- NEVER confirm how long a waitlist is
- NEVER imply clients must complete multiple visits before being offered an upgrade — the upgrade conversation happens during the FIRST visit consultation

== HARD RULES — NEVER DO THESE ==
- NEVER confirm specific appointment times or availability — you have no access to the calendar. Always say "grab a time that works for you on the booking link"
- NEVER confirm who their technician will be or staff availability
- NEVER promise same-day appointments
- NEVER quote package prices beyond the $99 intro offer
- NEVER offer discounts, promotions, or price matching
- NEVER say anything is "on sale" or "ending soon"
- NEVER promise specific results like "you'll lose X inches in X weeks"
- NEVER reference another client's results by name
- NEVER make FDA approval claims or clinical treatment claims
- NEVER advise on medication interactions or medical decisions
- NEVER confirm refund amounts or timelines beyond the standard deposit policy
- NEVER say "I'll have someone call you" — you cannot guarantee that
- NEVER confirm how long a waitlist is

== WHAT ABS IS AND IS NOT ==
ABS is NOT: liposuction, surgery, weight-loss injections
ABS IS: body contouring, stubborn fat reduction, inches lost, confidence building, helping improve areas resistant to diet and exercise

== COMMON QUESTIONS ==
"Does it hurt?" → Generally comfortable and non-invasive. Most clients find it relaxing. Many describe it as spa-like.

"How many sessions do I need?" → Depends on goals, area, and starting point. Most clients achieve better results through a series. That's something we go over during your consultation.

"How soon will I see results?" → Many clients notice changes within the first few visits. Your body continues improving for weeks as it processes and eliminates dissolved fat cells.

"Do results last?" → Once fat cells are dissolved, they're gone. As long as you maintain your weight, the changes are lasting.

"Can I bring someone?" → Of course! Guests are welcome.

"Is there parking?" → Yes, free parking in the business park lot.

"Do you accept insurance?" → Body sculpting isn't covered by insurance, but we do accept HSA/FSA cards and offer financing through CareCredit, Cherry, Afterpay, Affirm, and Klarna.

"How much is everything?" / "What are your package prices?" → Package pricing is personalized based on your goals and treatment area — that's something we go over during your consultation so we can give you the most accurate recommendation. The best first step is to get in for your $99 intro visit!

"Can I come a different day?" / Rescheduling intro visit → Give them the reschedule link: https://services.msgsndr.com/urls/l/85XJNne5qG

"I am an existing member" / "I'm an existing client" / any indication they already have a package → Immediately say "No problem! The easiest way to get that changed is to give us a call at (770) 977-1163 or shoot us an email at info@atlbodysculpt.com and we'll get you taken care of!"

== RESCHEDULING RULES ==
- If someone says they need to reschedule and you don't know if they are a new or existing client, ALWAYS ask first:
  "Of course! Are you looking to reschedule your first visit, or are you an existing member?"
- If they confirm it's their FIRST VISIT → Give them: https://services.msgsndr.com/urls/l/85XJNne5qG
- If they confirm they are an EXISTING MEMBER → Say "No problem! The easiest way to get that changed is to give us a call at (770) 977-1163 or shoot us an email at info@atlbodysculpt.com and we'll get you taken care of!"

== FLAGGING FOR TERRY ==
If any of the following situations come up, respond warmly to the person but add the flag code at the very END of your response on its own line. Terry will never see this — it's just for routing.

[FLAG:MEDICAL] → Any mention of medical conditions, health concerns, medications, pregnancy, or anything from the not-a-candidate list
[FLAG:URGENT] → Complaints, refund requests, upset or frustrated clients, anyone threatening to dispute a charge
[FLAG:MANUAL] → Existing client needs appointment change beyond intro visit rescheduling
[FLAG:REVIEW] → Anything you genuinely don't know how to answer or that feels outside your scope

== EXAMPLE RESPONSES ==
Lead: "how much is it and what do you get"
Bot: "Hey! For $99 you get a full body assessment, a 3D ShapeScale body scan, your first in-house treatment, a lymphatic massage, and vibration therapy — plus 2 take-home treatments. Just a $25 deposit to lock in your spot, and it goes toward your balance. Want me to send you the booking link? 😊"

Lead: "does it hurt"
Bot: "Not at all! Most clients say it feels really relaxing — almost like a spa experience. The treatments are completely non-invasive and comfortable."

Lead: "I need to think about it"
Bot: "Totally understand! The $25 deposit is fully refundable so there's really no risk. Would it help to just lock in a time and you can always reschedule if needed?"

Client: "I need to reschedule my appointment"
Bot: "Of course, no problem at all! You can pick a new time right here → https://services.msgsndr.com/urls/l/85XJNne5qG"

Lead: "do you take insurance"
Bot: "We don't work with insurance since body sculpting isn't covered, but we do accept HSA/FSA cards and have financing options like CareCredit, Cherry, and Afterpay. Happy to go over options during your visit!"
"""

# ── Helper: Get GHL conversation history ─────────────────────────────────────
def get_conversation_history(contact_id):
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            return []

        convo_id = convos[0]["id"]
        r2 = requests.get(
            f"{GHL_BASE_URL}/conversations/{convo_id}/messages",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"limit": 20}
        )
        messages = r2.json().get("messages", {}).get("messages", [])

        history = []
        for msg in reversed(messages):
            direction = msg.get("direction", "")
            body = msg.get("body", "").strip()
            if not body:
                continue
            role = "user" if direction == "inbound" else "assistant"
            history.append({"role": role, "content": body})

        return history
    except Exception as e:
        print(f"Error fetching GHL history: {e}")
        return []


# ── Helper: Check if a human recently replied ────────────────────────────────
def human_recently_replied(contact_id, grace_minutes=15):
    """Returns True if a human manually replied within the grace period."""
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            return False

        convo = convos[0]
        last_action = convo.get("lastOutboundMessageAction", "automated")
        last_message_date = convo.get("lastMessageDate", 0)

        if last_action != "manual":
            return False

        # Check if manual reply was within grace period
        import time
        now_ms = int(time.time() * 1000)
        age_minutes = (now_ms - last_message_date) / 1000 / 60

        if age_minutes <= grace_minutes:
            print(f"🤚 Human replied {round(age_minutes, 1)} mins ago — bot staying quiet")
            return True
        else:
            print(f"⏰ Human replied {round(age_minutes, 1)} mins ago — grace period expired, bot responding")
            return False

    except Exception as e:
        print(f"Error checking handoff status: {e}")
        return False

# ── Helper: Send message via GHL ─────────────────────────────────────────────
def send_ghl_message(contact_id, message):
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/conversations/search",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-04-15"},
            params={"contactId": contact_id, "limit": 1}
        )
        convos = r.json().get("conversations", [])
        if not convos:
            print("No conversation found for contact")
            return False

        convo_id = convos[0]["id"]
        r2 = requests.post(
            f"{GHL_BASE_URL}/conversations/messages",
            headers={
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-04-15"
            },
            json={"type": "SMS", "conversationId": convo_id, "contactId": contact_id, "message": message}
        )
        print(f"GHL send: {r2.status_code} {r2.text}")
        return r2.status_code == 200
    except Exception as e:
        print(f"Error sending GHL message: {e}")
        return False

# ── Helper: Email alert to Terry ─────────────────────────────────────────────
def alert_terry(flag_type, contact_name, inbound, reply_sent):
    subjects = {
        "MEDICAL": "🏥 ABS Bot — Medical Question Flagged",
        "URGENT":  "🚨 ABS Bot — URGENT: Complaint or Refund Request",
        "MANUAL":  "📅 ABS Bot — Existing Client Needs Manual Booking",
        "REVIEW":  "👀 ABS Bot — Message Needs Your Review"
    }
    subject = subjects.get(flag_type, "ABS Bot — Flag for Review")
    body = f"""Hey Terry,

The ABS bot flagged a message that needs your attention.

Contact: {contact_name}
Flag Type: {flag_type}

Their message:
"{inbound}"

What the bot replied:
"{reply_sent}"

Log into GHL to follow up.

— ABS Bot
"""
    # Print to terminal for now (email setup can be added later)
    print(f"\n{'='*60}")
    print(f"⚠️  ALERT TO TERRY: {subject}")
    print(body)
    print(f"{'='*60}\n")

# ── Main Bot Route ────────────────────────────────────────────────────────────
def register_ghl_bot(app):
    @app.route("/ghl-bot", methods=["POST"])
    def ghl_bot():
        data = request.json or request.form.to_dict()
        print(f"\n📩 GHL Bot received: {data}")

        contact_id = data.get("contact_id")
        msg = data.get("message", ""); inbound_message = str(msg.get("body", msg) if isinstance(msg, dict) else msg).strip()
        contact_name = data.get("contact_name", "there")

        if not contact_id or not inbound_message:
            return jsonify({"error": "missing contact_id or message"}), 400

        # Skip single-letter replies — your automations handle those
        if inbound_message.strip().upper() in ["A", "B", "C"]:
            print(f"⏭️  Skipping single-letter reply: {inbound_message}")
            return jsonify({"status": "skipped", "reason": "automation handles this"})

        # Handoff check temporarily disabled
        # if human_recently_replied(contact_id, grace_minutes=45):
        #     return jsonify({"status": "skipped", "reason": "human recently replied — in grace period"})

        # 1. Get conversation history for context
        history = get_conversation_history(contact_id)
        if not history or history[-1].get("content") != inbound_message:
            history.append({"role": "user", "content": inbound_message})

        if not history:
            history = [{"role": "user", "content": inbound_message}]

        # 2. Ask Claude what to say
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=ABS_SYSTEM_PROMPT,
                messages=history
            )
            reply_text = response.content[0].text.strip()
        except Exception as e:
            print(f"Claude error: {e}")
            return jsonify({"error": str(e)}), 500

        # 3. Check if Claude flagged this for Terry
        flag = None
        for flag_type in ["MEDICAL", "URGENT", "MANUAL", "REVIEW"]:
            flag_tag = f"[FLAG:{flag_type}]"
            if flag_tag in reply_text:
                flag = flag_type
                reply_text = reply_text.replace(flag_tag, "").strip()
                break

        # 4. Send the reply
        send_ghl_message(contact_id, reply_text)

        # 5. Alert Terry if flagged
        if flag:
            alert_terry(flag, contact_name, inbound_message, reply_text)

        print(f"✅ Bot replied to {contact_name}: {reply_text}")
        if flag:
            print(f"🚩 Flagged for Terry: {flag}")

        return jsonify({"status": "ok", "reply": reply_text, "flagged": flag})
