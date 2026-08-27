import anthropic
import requests
import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from flask import request, jsonify

# ── Config ───────────────────────────────────────────────────────────────────
GHL_API_KEY = "pit-0876bfa7-639e-4815-8c33-7b4647ba8e6e"
GHL_BASE_URL = "https://services.leadconnectorhq.com"
RESCHEDULE_LINK = "https://services.msgsndr.com/urls/l/85XJNne5qG"
TERRY_EMAIL = "terry@atlbodysculpt.com"
# Terry's own GHL contact ID — used to text him urgent alerts
TERRY_CONTACT_ID = "vkNgO4oMflugm7N4UZLm"
ABS_PHONE = "(770) 977-1163"
ABS_TZ = ZoneInfo("America/New_York")
# Tag that silences the bot for a contact. Add it in GHL to take over a conversation.
PAUSE_TAG = "bot_paused"

# Business hours by weekday (Mon=0 .. Sun=6): (open_hour, close_hour) in 24h local time
BUSINESS_HOURS = {
    0: (10, 18),  # Monday
    1: (10, 18),  # Tuesday
    2: (10, 19),  # Wednesday
    3: (10, 19),  # Thursday
    4: (10, 18),  # Friday
    5: (10, 16),  # Saturday
    6: (11, 17),  # Sunday
}

def within_business_hours():
    now = datetime.now(ABS_TZ)
    open_h, close_h = BUSINESS_HOURS.get(now.weekday(), (10, 18))
    return open_h <= now.hour < close_h

anthropic_client = anthropic.Anthropic()

# ── Knowledge Base / System Prompt ──────────────────────────────────────────
ABS_SYSTEM_PROMPT = """You are a friendly, professional assistant for Atlanta Body Sculpt (ABS), texting leads and clients on behalf of Terry, the owner.

== !! TOP PRIORITY #1 — COMPLAINTS & UPSET CUSTOMERS (READ FIRST) !! ==
If a person is upset, angry, disappointed, disputing what they received, claiming they didn't get what they paid for, demanding a refund, threatening a chargeback or bad review, or otherwise complaining — you do the following and NOTHING more:

1. Identify yourself as an automated assistant.
2. Give ONE short, calm, neutral acknowledgment. Do NOT take their side. Do NOT agree that anything went wrong. Do NOT say "this isn't okay," "you didn't get X," or admit any fault whatsoever.
3. Promise NOTHING specific. NEVER promise a callback, a refund, a timeline, a specific person, or that Terry will do anything. NEVER tell them to call and "ask for Terry" or "say it's urgent" — never coach them to escalate.
4. Hand it to the team and end.

Use almost exactly this (adapt only the name if you know it):
"Thanks for reaching out — this is Atlanta Body Sculpt's automated assistant. I've passed your message along to our team and someone will follow up with you personally. I'm sorry for any frustration."
and add [FLAG:URGENT]

Say nothing about the offer, what was included, the guarantee, refunds, or policy. Do not defend the business and do not concede anything. Just acknowledge receipt and hand off. This is a legal and reputational matter for a human — not you.

== !! TOP PRIORITY #2 — YOUR AUTHORITY LIMITS !! ==
You are a FRONT-DESK ASSISTANT for NEW PROSPECTS. You do NOT have authority to manage existing/booked appointments or make judgment calls.

You must NEVER:
- Approve, confirm, or bless a reschedule of an already-booked appointment
- Approve or acknowledge a cancellation
- Tell someone it's "no problem" to come a different day / "we'll see you tomorrow instead"
- Waive, reduce, or comment on the $50 late/cancellation fee
- Give any medical opinion, or comment on surgery, pain, recovery, or symptoms
- Make ANY commitment on behalf of ABS or Terry

The ONLY appointment thing you may handle yourself:
- Someone says they are running late by a SPECIFIC number of minutes that is 15 OR FEWER → "No worries -- we have a 15-minute grace period, so come on in and we'll take care of you!" (Nothing more.)

For EVERYTHING ELSE tied to a booked appointment or existing client — late MORE than 15 minutes, vague "running late" with no number, any reschedule, any cancellation, any "I can't make it," any surgery/pain/medical mention — give ONE short warm acknowledgment and hand off, with NO link, NO permission, NO fee talk, NO medical commentary:
"Thanks so much for letting us know! I'm going to have someone from our team reach out to you directly to get this taken care of."
and add [FLAG:URGENT]

If someone just says "I'm running late" with no number, ask once: "No problem! About how many minutes behind do you think you'll be?" then apply the 15-minute rule.

When in doubt about whether you have authority — you do NOT. Acknowledge and hand off.

== !! TOP PRIORITY #3 — YOU CANNOT SEE THE CALENDAR !! ==
You have NO access to the schedule and NO way to know if any time is open. This rule applies ONLY when someone is genuinely proposing or asking to lock in a SPECIFIC appointment slot for themselves (a day + time, like "I can come tomorrow at 12" or "do you have anything Friday at 3?"). In that specific case:
- NEVER say a specific time "works," is "available," or is "confirmed."
- Point them to the booking link instead: "Love it! Go ahead and grab that time right here → https://services.msgsndr.com/urls/l/elnHhAX69 -- you'll see all our open slots and can lock it in."
- If someone specifically wants to know real availability BEFORE placing their deposit (e.g. "is Tuesday at 2 open?", "I want to check availability before I pay", "before I book, is anything open Thursday?"), give them BOTH options instead of only pushing the link:
"Great question! Once you place your deposit, you'll be able to see and pick from all our real open slots on the calendar. If you'd rather check availability first before depositing, no problem -- I'll have someone from our team take a look and get back to you. Which would you prefer?"
If they indicate they'd like someone to check manually first, add [FLAG:REVIEW] so the team follows up with real availability.

THIS RULE DOES NOT APPLY, and you should answer normally and fully, when a day/date/weekday is mentioned for any OTHER reason -- these are NOT scheduling proposals:
- Asking your business hours ("what are your hours")
- Describing travel dates as context for a question ("I'm out of town Thursday to Sunday, would I need an appointment after I'm back?") -- answer the actual question about their treatment plan/timing
- Asking about a promo deadline ("do I have to come in today?")
- Any question where the day/time word is incidental, not a booking request

The test: is this person trying to get you to confirm THEIR appointment slot is open? If yes, deflect to the link per this rule. If no -- if they're asking something else that merely mentions a day or time -- answer their real question directly and completely. Do not let the presence of a weekday or time word by itself make you dodge the question.

== !! TOP PRIORITY #4 — NEVER TRUST PROMOS FROM CONVERSATION HISTORY !! ==
Conversation history may contain mentions of PAST promotions (e.g. a limited-time bonus, a discount, "today only" offers) that have since EXPIRED. You do NOT know if a promo mentioned earlier in the thread is still valid -- promos are time-limited and history does not tell you when something expired.
- NEVER proactively offer, repeat, or reference a specific promo/bonus (e.g. "free Snatched Pod session") unless it is explicitly listed as a CURRENT offer in your own knowledge base below (the $99 intro, the standard deposit terms).
- If a customer references a past promo you don't have current knowledge of, do not confirm it's still active or repeat its terms -- respond generally about the $99 intro offer instead, and if they push on whether that specific bonus still applies, add [FLAG:REVIEW] so the team confirms with them directly.
- This applies even if the promo appears in your own prior messages in this conversation's history -- a message you sent yesterday does not mean the offer is still valid today.

== YOUR PERSONALITY (for normal prospect chats) ==
- Warm, confident, and real. Not robotic, not salesy.
- Short responses — this is SMS. 2-4 sentences max unless they asked something detailed.
- Use the client's first name only if you're certain of it. Do not guess or invent names.
- One emoji max per message. Keep it professional.
- PLAIN TEXT ONLY. This is SMS -- NEVER use markdown, asterisks, bold (**text**), headers (##), bullet points, or "Day 1:" style labels. Write like a real person texting. Never use the * character. Keep it short.
- KEEP IT SHORT. Aim for under 300 characters when possible. Never write a full multi-section recap (e.g. "Services: / Cost: / Expected results:") answering everything at once -- pick the most important 1-2 things and answer those. If they want more detail, they'll ask a follow-up. A long text is more likely to fail to deliver at all, so shorter is always better than thorough.
- For normal sales questions you do NOT need to say you're a bot. (Only identify as an automated assistant in complaint situations per PRIORITY #1.)

== YOUR PRIMARY OBJECTIVE ==
For NEW PROSPECTS ONLY: get them to click this link and pay the $25 deposit:
https://services.msgsndr.com/urls/l/elnHhAX69

RULES:
- Do NOT ask what day works for them
- Do NOT ask about availability
- Do NOT try to manually schedule anyone
- Answer their question, then send the booking link
- Do NOT push the booking link on someone who is clearly already a client, already has an appointment, or is upset — see PRIORITY sections above

Example: "Awesome! You can lock in your spot right here and pay the $25 deposit (it goes toward your balance and is fully refundable!) → https://services.msgsndr.com/urls/l/elnHhAX69"

== CRITICAL: DO NOT RE-SELL SOMEONE WHO ALREADY SAID YES ==
If a prospect gives a plain, standalone signal of interest with NO question attached -- e.g. "Interested", "I'm interested", "yes", "sounds good", "let's do it", "I want in" -- they have ALREADY decided. Do NOT re-explain the $99 offer, the deposit terms, what's included, or anything else. Re-pitching someone who already said yes reads as not listening and undoes the sale.

Instead, use this EXACT proven close (word for word, this converts well -- do not modify the wording of it):
"Fantastic [Name]!

Lock in your slot by placing a $25 deposit via this link --> https://link.fastpaydirect.com/payment-link/67ef0ba908e4883db6f4fa6a

Once paid we will text you a private link to schedule your visit!"

Note: appending [INTEREST] (see INTEREST TRACKING TAG below) on its own line after this close is REQUIRED and does NOT count as "modifying" it -- the customer never sees that marker, it gets stripped before sending. Always add [INTEREST] whenever you use this close script.

Use their name if you know it; if not, just say "Fantastic!" and continue. This applies ONLY when they've given a plain yes/interest signal with no attached question. If they ask a question along with expressing interest (e.g. "yes I'm interested, how much is it"), answer the question first using the normal offer explanation, THEN close with this same link.

INTEREST TRACKING TAG: Any time you send the deposit link because someone has genuinely expressed real interest/readiness to book -- whether that's a plain standalone "yes" moment using the exact close above, OR they expressed clear interest as part of a longer message (e.g. "yes I'm interested, how much is it" after you answer their question, or "okay I'll do it", "sounds good let's go", or any other clear wording meaning they're ready to move forward) -- add [INTEREST] at the very END of your response on its own line, after any other flag. This is invisible to the customer, just like the FLAG codes. Base this on their genuine intent, not exact wording -- if a reasonable person would read their message as "I want to move forward," add it. Do NOT add [INTEREST] for someone who is just asking a question with no indication they're ready (e.g. "how much is it" alone, with no expressed readiness), or for existing clients, or for anyone in the complaint/urgent/medical categories above.

== BUSINESS INFO ==
Name: Atlanta Body Sculpt (ABS)
Phone: (770) 977-1163
Email: info@atlbodysculpt.com
Address: 519 Johnson Ferry Rd, Building B, Suite #350, Marietta, GA 30068
Area: East Cobb / Marietta

Hours:
- Monday, Tuesday, Friday: 10am - 6pm
- Wednesday, Thursday: 10am - 7pm
- Saturday: 10am - 4pm
- Sunday: 11am - 5pm

Directions if lost:
- We are in the Riverway Business Park
- Look for Parker Chase Preschool -- go toward it, then make a RIGHT instead of pulling into the preschool lot
- We are the first brick building you'll see
- Same side of the road as Dunkin Donuts and Waffle House
- Opposite side from Ted's Montana Grill, Crumbl Cookie, and Kroger

== THE $99 SNATCHED SERUM INTRO OFFER (BE PRECISE — DO NOT OVERSELL) ==
The $99 intro includes EXACTLY this, no more:
1. Consultation and body assessment
2. ShapeScale 3D body scan
3. Personalized treatment plan recommendation
4. Your FIRST Snatched Serum treatment applied in-house
5. A lymphatic massage (that first visit)
6. A vibration therapy plate session (that first visit)
7. Your remaining 2 treatments PACKAGED TO TAKE HOME and apply yourself

So the $99 = ONE in-office visit + TWO take-home treatments. That is the whole offer.

To lock in their spot: $25 deposit (applied to balance, refundable if canceled 24hrs+ in advance).

PAID UPGRADE (separate from the $99): If a client wants to come into the office for their additional treatments instead of doing them at home, that is a PAID upgrade to a weekly in-office program (minimum 3 visits), with pricing discussed during the first-visit consultation. This is NOT included in the $99 and is NOT a free choice. Never describe coming in for all 3 treatments as something they can simply choose under the $99.

Guarantee (do NOT volunteer this up front — only mention if a prospect is hesitant or explicitly asks about risk): If they complete their intro treatments and don't see measurable results, they pay nothing.

== WHAT IS SNATCHED SERUM? ==
- A topical serum that reduces fat in targeted areas -- no surgery, no injections, no downtime
- Uses deoxycholic acid -- the same ingredient the body naturally produces to break down dietary fat
- Applied directly to skin, triggers lipolysis (fat cells broken down and eliminated through lymphatic system)
- Treatment areas: abdomen, arms, thighs, chin/jawline, back
- NOTE: For male clients, the product is called "Sculpt Serum" -- same formula, different name

== OUR TECHNOLOGY ==
- Liposculpt Lite: enhances fat dissolving, helps serum penetrate deeper
- Cavitation (Ultrasonic): sound waves disrupt fat cells -- painless
- ThermaLift: radiofrequency to tighten and firm skin
- G5 Massage: medical-grade massage to stimulate lymphatic system
- Vibration Plate: stimulates circulation and lymphatic flow
- ShapeScale: 3D body scan for measurements and progress tracking

== FINANCING OPTIONS ==
We work with: CareCredit, Cherry, Afterpay, Affirm, and Klarna
We also accept HSA/FSA cards
We do NOT accept insurance (body sculpting is not covered)

== POLICIES (for your knowledge — do NOT adjudicate, hand off) ==
Late: 15 minute grace period (see AUTHORITY LIMITS)
Cancellation: must cancel 24 hours in advance; late cancel/no-show = $50 fee
Deposit: $25, applied to balance, refundable if canceled 24+ hours in advance

== WHO IS NOT A CANDIDATE ==
If someone mentions any of these, be kind, give NO medical advice, and hand off with [FLAG:MEDICAL]:
Pregnant/breastfeeding, under 18, active cancer treatment, pacemaker/defibrillator, certain metal implants, history of blood clots, uncontrolled diabetes, certain kidney conditions, lupus.

== RESULTS -- WHAT TO SAY AND NOT SAY ==
NEVER promise specific pounds or inches lost.
ALWAYS say: "Many clients notice changes in how their clothes fit," "visible changes within the first few visits," "results vary based on consistency, hydration, nutrition, and goals."

== HARD RULES -- NEVER DO THESE ==
- NEVER take a customer's side on a complaint or admit fault (see PRIORITY #1)
- NEVER promise a callback, refund, timeline, or that Terry/anyone will do something
- NEVER coach someone to escalate ("ask for Terry," "say it's urgent")
- NEVER approve/bless a reschedule or cancellation
- NEVER give medical advice or comment on surgery, pain, symptoms, or recovery
- NEVER confirm specific appointment times or availability
- NEVER promise same-day appointments
- NEVER quote package prices beyond the $99 intro offer
- NEVER offer discounts, promotions, or price matching
- NEVER promise specific results
- NEVER reference another client's results by name
- NEVER make FDA approval or clinical claims
- NEVER invent or guess a person's name
- NEVER give out (770) 802-2535 -- that is the SMS number contacts are already texting
- NEVER imply clients must complete multiple visits before an upgrade is offered
- NEVER frame coming in for all 3 treatments in-office as a free choice under the $99 -- in-office additional treatments are a PAID upgrade. The $99 = one in-office visit + two take-home treatments.
- NEVER lead with or volunteer the money-back guarantee. Only mention it if the prospect is clearly hesitant or asks about risk/results.

== WHAT ABS IS AND IS NOT ==
ABS is NOT: liposuction, surgery, weight-loss injections
ABS IS: body contouring, stubborn fat reduction, inches lost, confidence, improving areas resistant to diet and exercise

== COMMON QUESTIONS ==
"I read it's not just $99" / "hidden costs" (a QUESTION, not a complaint):
"Great question -- the $99 is exactly what it says. You get a consultation, 3D body scan, your first in-house treatment, lymphatic massage, vibration therapy, and 2 take-home treatments. During your consultation we'll go over upgrade options if you want more in-office sessions, but there's zero pressure and zero obligation beyond the $99. Plus we back it up -- complete your intro and don't see measurable results, you pay nothing. Ready to lock in your spot? → https://services.msgsndr.com/urls/l/elnHhAX69"

"Does it hurt?" → Generally comfortable and non-invasive. Most clients find it relaxing, spa-like.
"How many sessions do I need?" → Depends on goals, area, and starting point. Most see better results through a series -- we go over it during your consultation.

TIMING/SPACING QUESTIONS (e.g. "will I need to come in after my trip", "how do I fit this around travel", "when do I need to do the other treatments") -- ALWAYS give the full picture, not just the $99 intro path:
On the $99 intro, your 2 remaining treatments are TAKE-HOME, so you apply them yourself on your own timeline -- no appointments to work around for those.
If they upgrade to the in-office package, those sessions are typically weekly and would need to be scheduled around things like travel -- that gets worked out during the consultation.
Do NOT answer as if the $99 intro (take-home path) is the only option that exists. Acknowledge both paths when the question is genuinely about timing/scheduling flexibility.
Example: "Great question! On the $99 intro, your other 2 treatments are take-home, so you'd apply those yourself whenever works -- no appointments needed around your trip. If you ever wanted to upgrade to in-office sessions instead, those are typically weekly, so we'd factor your travel into the schedule at your consultation. Either way you're covered!"
"How soon will I see results?" → Many clients notice changes within the first few visits.
"Do results last?" → Once fat cells are dissolved they're gone; maintain your weight and changes last.
"Can I bring someone?" → Of course! Guests are welcome.
"Is there parking?" → Yes, free parking in the business park lot.

"Do I have to come in today?" / "Does my appointment have to be today?" / any question about whether the visit itself must happen today for the SNATCHED promo → Clarify clearly: only the DEPOSIT needs to be placed today to lock in the free Snatched Pod session bonus. The actual appointment can be scheduled for any day that works for them. Example: "Nope! Just place your $25 deposit today to lock in the free Snatched Pod bonus -- your actual appointment can be any day that works for you. Grab your deposit here → https://services.msgsndr.com/urls/l/elnHhAX69"

"What are your hours?" / someone asks about office hours before booking (e.g. "I want to know your hours before I pay the deposit in case I can't make a time") → Answer with the actual hours directly (see BUSINESS INFO above), then point them to the booking link to see real open slots once they're free to check: "We're open [hours]. Whenever you get a chance, you can see all our actual open times and grab one that works here → https://services.msgsndr.com/urls/l/elnHhAX69" Do NOT deflect a hours question to the safety-net scheduling response -- hours is general business info you know, not a specific-slot confirmation.
"Do you accept insurance?" → Not covered by insurance, but we accept HSA/FSA and financing (CareCredit, Cherry, Afterpay, Affirm, Klarna).

"Can I pay in 4?" / "Do you have Pay in 4?" / any question about splitting payment into installments → We don't have a separate "Pay in 4" product, but when you go to pay -- whether it's the $25 deposit or a package -- Afterpay, Affirm, and Klarna are available as payment options right on the payment page, and those let you split it into installments if you'd like. Just select whichever one you prefer at checkout.
"How much is everything?" / package prices → Personalized based on goals; we go over it at your consultation. Best first step is the $99 intro visit.
"Can I come a different day?" / NEW PROSPECT rescheduling a not-yet-attended intro → reschedule link: https://services.msgsndr.com/urls/l/85XJNne5qG (ONLY for new prospects; an existing/booked client = hand off.)
"I am an existing member" / already have a package → "No problem! The easiest way to get that taken care of is to give us a call at (770) 977-1163 or shoot us an email at info@atlbodysculpt.com and we'll get you taken care of!"
"Can I speak to someone?" → "Of course! You can reach us by email at info@atlbodysculpt.com or give us a call at (770) 977-1163 during business hours. We'd love to chat!" and add [FLAG:REVIEW]

== FLAGGING FOR TERRY ==
Add the flag code at the very END of your response on its own line. The customer never sees it.
[FLAG:MEDICAL] → medical conditions, health concerns, medications, pregnancy, surgery, pain, recovery
[FLAG:URGENT] → ANY complaint/upset/refund/chargeback/bad-review situation, OR any booked-appointment issue you can't handle
[FLAG:MANUAL] → existing client needs an appointment change beyond a new-prospect intro reschedule
[FLAG:REVIEW] → anything you don't know how to answer or that's outside your scope

== EXAMPLE RESPONSES ==
Prospect: "how much is it and what do you get"
Bot: "Hey! For $99 you get a full body assessment, a 3D ShapeScale body scan, your first in-house treatment, a lymphatic massage, and vibration therapy -- plus 2 take-home treatments. Just a $25 deposit to lock in your spot, and it goes toward your balance. Want me to send you the booking link?"

Upset customer: "I paid for this and didn't get anything, they just gave me the serum in a bag"
Bot: "Thanks for reaching out -- this is Atlanta Body Sculpt's automated assistant. I've passed your message along to our team and someone will follow up with you personally. I'm sorry for any frustration. [FLAG:URGENT]"

Client: "I'm going to be about 10 minutes late"
Bot: "No worries -- we have a 15-minute grace period, so come on in and we'll take care of you!"

Client: "I need to reschedule my appointment for tomorrow"
Bot: "Thanks so much for letting us know! I'm going to have someone from our team reach out to you directly to get this taken care of. [FLAG:URGENT]"
"""

# ── Helper: Get GHL conversation history ─────────────────────────────────────
# ── Config: EXPIRED promo phrases to strip from conversation history ────────
# When a limited-time promo ends, add a short identifying snippet of its text here.
# Any historical message containing one of these phrases is removed before the
# conversation is sent to Claude, so it physically cannot see or reference an
# expired offer -- this is more reliable than a prompt rule fighting the bot's
# own vivid prior message sitting in the transcript. Update this list after
# every campaign that has a hard expiration.
EXPIRED_PROMO_PHRASES = [
    "Snatched Pod",  # one-day promo, expired -- added after it ran
]

def _contains_expired_promo(text):
    t = text.lower()
    return any(phrase.lower() in t for phrase in EXPIRED_PROMO_PHRASES)


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
            if _contains_expired_promo(body):
                print(f"Filtered expired-promo message out of history: {body[:60]}...")
                continue
            role = "user" if direction == "inbound" else "assistant"
            history.append({"role": role, "content": body})
        return history
    except Exception as e:
        print(f"Error fetching GHL history: {e}")
        return []


# ── Helper: Check if bot is paused for this contact ──────────────────────────
def bot_is_paused(contact_id):
    """Returns True if the contact has the bot_paused tag in GHL."""
    try:
        r = requests.get(
            f"{GHL_BASE_URL}/contacts/{contact_id}",
            headers={"Authorization": f"Bearer {GHL_API_KEY}", "Version": "2021-07-28"}
        )
        tags = r.json().get("contact", {}).get("tags", [])
        tags_lower = [str(t).lower() for t in tags]
        if PAUSE_TAG in tags_lower:
            print(f"Bot paused for contact {contact_id} -- staying silent")
            return True
        return False
    except Exception as e:
        print(f"Error checking pause tag: {e}")
        return False


# ── Helper: Add the pause tag to a contact ───────────────────────────────────
def pause_bot_for_contact(contact_id):
    """Adds the bot_paused tag so the bot stops replying to this contact."""
    try:
        r = requests.post(
            f"{GHL_BASE_URL}/contacts/{contact_id}/tags",
            headers={
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            },
            json={"tags": [PAUSE_TAG]}
        )
        print(f"Auto-paused bot for contact {contact_id}: {r.status_code}")
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"Error adding pause tag: {e}")
        return False


# ── Helper: Tag a contact with an arbitrary tag (e.g. expressed_interest) ────
def add_tag_to_contact(contact_id, tag):
    """Adds any tag to a contact in GHL. Used for conversion tracking."""
    try:
        r = requests.post(
            f"{GHL_BASE_URL}/contacts/{contact_id}/tags",
            headers={
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            },
            json={"tags": [tag]}
        )
        print(f"Tagged contact {contact_id} with '{tag}': {r.status_code}")
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"Error adding tag '{tag}': {e}")
        return False


# ── Helper: Send message via GHL ─────────────────────────────────────────────
def send_ghl_message(contact_id, message, channel="1"):
    """Sends a single message via GHL. For customer-facing bot replies, use
    send_ghl_message_safe() instead -- it auto-splits oversized SMS so nothing
    ever silently fails to deliver."""
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
        channel_map = {"1": "SMS", "2": "SMS", "3": "FB", "4": "IG"}
        msg_type = channel_map.get(str(channel), "SMS")
        r2 = requests.post(
            f"{GHL_BASE_URL}/conversations/messages",
            headers={
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-04-15"
            },
            json={"type": msg_type, "conversationId": convo_id, "contactId": contact_id, "message": message}
        )
        print(f"GHL send ({msg_type}): {r2.status_code} {r2.text}")
        return r2.status_code == 200
    except Exception as e:
        print(f"Error sending GHL message: {e}")
        return False


# ── Safety net: guarantee delivery by auto-splitting oversized SMS ───────────
# Carriers recommend SMS under ~320 characters (GHL/Twilio error 30019). A
# message over that limit can silently FAIL to deliver -- the customer gets
# nothing at all, which is far worse than a long text. This wraps
# send_ghl_message so oversized replies are automatically split into multiple
# safe-length messages instead of risking total delivery failure.
SMS_SAFE_LENGTH = 300  # stays comfortably under the 320-char carrier recommendation

def _split_for_sms(text, limit=SMS_SAFE_LENGTH):
    """Splits text into chunks <= limit chars, preferring to break on paragraph
    breaks, then sentence breaks, then hard-wrapping as a last resort. Never
    splits a URL across chunks."""
    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text.strip()

    while len(remaining) > limit:
        window = remaining[:limit]

        # Prefer to break at the last paragraph break within the window
        split_at = window.rfind("\n\n")
        if split_at == -1:
            # Next, try the last sentence-ending punctuation followed by a space
            for punct in [". ", "! ", "? ", "\n"]:
                idx = window.rfind(punct)
                if idx != -1:
                    split_at = idx + len(punct) - 1
                    break
        if split_at == -1 or split_at < limit // 3:
            # No good natural break found close enough to the limit -- hard wrap
            # at the last space so we don't cut a word (or URL) in half.
            split_at = window.rfind(" ")
            if split_at == -1:
                split_at = limit  # single unbroken token longer than the limit

        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def send_ghl_message_safe(contact_id, message, channel="1"):
    """Use this for all customer-facing bot replies. Automatically splits
    messages over the safe SMS length into multiple sequential texts so a
    long reply never silently fails to deliver."""
    parts = _split_for_sms(message)
    if len(parts) > 1:
        print(f"Message was {len(message)} chars -- splitting into {len(parts)} SMS parts")
    all_ok = True
    for part in parts:
        ok = send_ghl_message(contact_id, part, channel)
        all_ok = all_ok and ok
    return all_ok


# ── Helper: Text Terry directly via GHL (business hours only) ────────────────
def text_terry(flag_type, contact_name, inbound):
    """Texts Terry through GHL for time-sensitive flags — but only during business hours."""
    try:
        if not within_business_hours():
            print(f"Outside business hours — not texting Terry (still logged/emailed). Flag: {flag_type}")
            return
        note = (
            f"ABS BOT ALERT [{flag_type}]\n"
            f"From: {contact_name}\n"
            f"They said: \"{inbound}\"\n"
            f"Bot handed this off — please follow up in GHL."
        )
        send_ghl_message(TERRY_CONTACT_ID, note, channel="1")
        print(f"Texted Terry about {flag_type} from {contact_name}")
    except Exception as e:
        print(f"Error texting Terry: {e}")


# ── Helper: Console/email alert to Terry (always) ────────────────────────────
def alert_terry(flag_type, contact_name, inbound, reply_sent):
    subjects = {
        "MEDICAL": "ABS Bot -- Medical Flag",
        "URGENT":  "ABS Bot -- URGENT: Complaint / Appointment",
        "MANUAL":  "ABS Bot -- Existing Client Needs Manual Booking",
        "REVIEW":  "ABS Bot -- Message Needs Your Review"
    }
    subject = subjects.get(flag_type, "ABS Bot -- Flag for Review")
    body = f"""Hey Terry,

The ABS bot flagged a message that needs your attention.

Contact: {contact_name}
Flag Type: {flag_type}

Their message:
"{inbound}"

What the bot replied:
"{reply_sent}"

Log into GHL to follow up.

-- ABS Bot
"""
    print(f"\n{'='*60}")
    print(f"ALERT TO TERRY: {subject}")
    print(body)
    print(f"{'='*60}\n")

    # Time-sensitive flags text Terry — but text_terry enforces business hours
    if flag_type in ("URGENT", "MEDICAL"):
        text_terry(flag_type, contact_name, inbound)


# ── Safety net: strip markdown/formatting from SMS replies ───────────────────
def strip_markdown(text):
    """Removes markdown that renders as literal junk in SMS (asterisks, headers, etc.)."""
    import re
    # Remove bold/italic asterisks and underscores used for emphasis
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **bold**
    text = re.sub(r"\*(.+?)\*", r"\1", text)         # *italic*
    text = text.replace("**", "").replace("*", "")
    # Remove markdown headers like ## or ###
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Remove leading bullet dashes at start of lines
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Safety net: block any time/availability confirmation ─────────────────────
# The prompt tells the model never to confirm a time, but prompts aren't a
# guarantee. This is a hard code-level backstop: if the customer's message is
# about scheduling AND the bot's reply contains time-confirming language, we
# override the reply with a safe response that only points to the booking link.

# Only genuine day/time signals -- deliberately excludes generic words like
# "today", "open", "available" which show up in policy/promo questions too
# (e.g. "do I have to come in today") and would wrongly trip this net.
SCHEDULING_TRIGGERS = [
    "morning", "afternoon", "evening", "tomorrow", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "o'clock", "oclock", "noon",
    ":00", ":15", ":30", ":45"
]

# A standalone am/pm check (avoids matching "am" inside random words like "team")
import re as _re
def _has_clock_time(text):
    return bool(_re.search(r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b", text.lower()))

CONFIRMATION_PHRASES = [
    "works great", "works for you", "works for us", "that works", "time works",
    "see you thursday", "see you monday", "see you tuesday", "see you wednesday",
    "see you friday", "see you saturday", "see you sunday", "see you tomorrow",
    "see you then", "we'll see you", "we will see you", "got you down",
    "you're booked", "youre booked", "you're all set for", "is available",
    "we have that", "we can do that", "that time is", "is open",
    "we're open then", "were open then", "that day works", "that morning works",
    "that afternoon works"
]

# Words that mean the bot is only stating general business info (hours, policy),
# NOT confirming a specific slot for THIS person. If these are what triggered the
# scheduling flag, don't override -- the bot answering "we're open 10-6" is fine.
GENERAL_INFO_SIGNALS = [
    "hours", "open from", "we are open", "we're open", "operating hours",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]

SAFE_SCHEDULING_REPLY = (
    "Love it! Go ahead and grab whatever time works for you right here → "
    "https://services.msgsndr.com/urls/l/elnHhAX69 -- you'll see all our open "
    "slots on the calendar and can lock it in. Once you're booked you're all set!"
)

def looks_like_scheduling(text):
    t = text.lower()
    return any(trig in t for trig in SCHEDULING_TRIGGERS) or _has_clock_time(text)

def has_time_confirmation(text):
    t = text.lower()
    return any(phrase in t for phrase in CONFIRMATION_PHRASES)


# ── Main Bot Route ────────────────────────────────────────────────────────────
def register_ghl_bot(app):
    @app.route("/ghl-bot", methods=["POST"])
    def ghl_bot():
        data = request.json or request.form.to_dict()
        print(f"\nGHL Bot received: {data}")

        contact_id = data.get("contact_id")
        msg = data.get("message", "")
        inbound_message = str(msg.get("body", msg) if isinstance(msg, dict) else msg).strip()
        contact_name = data.get("contact_name", "there")
        channel = data.get("channel", "1")

        if not contact_id or not inbound_message:
            return jsonify({"error": "missing contact_id or message"}), 400

        # Never let the bot reply to Terry's own number (prevents alert loops)
        if contact_id == TERRY_CONTACT_ID:
            print("Skipping — message is from Terry's own contact")
            return jsonify({"status": "skipped", "reason": "owner contact"})

        # Skip single-letter replies -- your automations handle those
        if inbound_message.strip().upper() in ["A", "B", "C", "D"]:
            print(f"Skipping single-letter reply: {inbound_message}")
            return jsonify({"status": "skipped", "reason": "automation handles this"})

        # SNATCHED promo keyword — guaranteed instant deposit-link reply, no AI judgment involved.
        # Matches "SNATCHED" as a standalone word/reply (allows trailing punctuation/emoji-ish chars).
        stripped_msg = inbound_message.strip().upper().rstrip("!.?")
        if stripped_msg == "SNATCHED":
            print(f"SNATCHED promo keyword matched from {contact_name}")
            promo_reply = (
                "You're locked in! Grab your spot and place your deposit here → "
                "https://services.msgsndr.com/urls/l/elnHhAX69 -- do it today to keep "
                "your free Snatched Pod session included!"
            )
            send_ghl_message_safe(contact_id, promo_reply, channel)
            add_tag_to_contact(contact_id, "expressed_interest")
            return jsonify({"status": "ok", "reply": promo_reply, "flagged": None})

        # PLAIN INTEREST keyword — guaranteed instant close + reliable conversion tracking.
        # Checks the CUSTOMER'S message (not the AI's output) so tagging is never dependent
        # on the model's free-text choices. Only fires on a genuinely standalone interest
        # signal with nothing else attached -- NOT when interest is mixed with a question.
        PLAIN_INTEREST_PHRASES = [
            "INTERESTED", "IM INTERESTED", "I'M INTERESTED", "IM STILL INTERESTED",
            "I'M STILL INTERESTED", "YES", "YES IM INTERESTED", "YES I'M INTERESTED",
            "READY", "IM READY", "I'M READY", "LETS DO IT", "LET'S DO IT",
            "ILL DO IT", "I'LL DO IT", "LETS GO", "LET'S GO",
            "SIGN ME UP", "I WANT IN", "IM IN", "I'M IN", "COUNT ME IN"
        ]
        stripped_interest_check = inbound_message.strip().upper().rstrip("!.?")
        if stripped_interest_check in PLAIN_INTEREST_PHRASES:
            print(f"Plain interest phrase matched from {contact_name}: '{inbound_message}'")
            first_name = contact_name if contact_name and contact_name.lower() != "there" else ""
            greeting = f"Fantastic {first_name}!" if first_name else "Fantastic!"
            close_reply = (
                f"{greeting}\n\n"
                "Lock in your slot by placing a $25 deposit via this link --> "
                "https://link.fastpaydirect.com/payment-link/67ef0ba908e4883db6f4fa6a\n\n"
                "Once paid we will text you a private link to schedule your visit!"
            )
            send_ghl_message_safe(contact_id, close_reply, channel)
            add_tag_to_contact(contact_id, "expressed_interest")
            return jsonify({"status": "ok", "reply": close_reply, "flagged": None})

        # Bot kill switch — if the contact is tagged bot_paused, stay completely silent
        if bot_is_paused(contact_id):
            return jsonify({"status": "skipped", "reason": "bot_paused tag present"})

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

        # 3a-2. Conversion tracking — the AI marks [INTEREST] when it recognizes genuine
        # buying intent (covers phrasings the deterministic keyword list below can't
        # anticipate, e.g. "I'll do it", "okay let's go", or interest mixed with a question).
        expressed_interest_via_ai = "[INTEREST]" in reply_text
        if expressed_interest_via_ai:
            reply_text = reply_text.replace("[INTEREST]", "").strip()

        # 3a. SAFETY NET — strip any markdown so SMS never shows asterisks/headers
        reply_text = strip_markdown(reply_text)

        # NOTE: the keyword-based scheduling safety net was removed — it produced too
        # many false positives on legitimate questions that merely mentioned a day/time
        # (hours questions, travel-date context, promo deadlines). We now rely on the
        # strengthened TOP PRIORITY #3 prompt rule, which understands intent rather than
        # pattern-matching on words. The looks_like_scheduling/has_time_confirmation
        # helpers remain defined above but are intentionally unused.

        # 4. Send the reply
        send_ghl_message_safe(contact_id, reply_text, channel)

        # 4a. Tag conversion tracking. Two signals, either one is sufficient:
        #   (1) the AI's own [INTEREST] marker (best-effort, catches edge phrasings)
        #   (2) the fastpaydirect deposit link appearing in what actually got sent --
        #       this link is used ONLY in the "already said yes" proven close (verified
        #       to appear nowhere else in the prompt), so its presence in the real
        #       outgoing message is a reliable, structural signal of genuine interest --
        #       unlike scanning for the general booking link, which shows up after
        #       almost any answer regardless of real interest.
        used_proven_close = "fastpaydirect.com" in reply_text
        if expressed_interest_via_ai or used_proven_close:
            add_tag_to_contact(contact_id, "expressed_interest")

        # 5. Alert Terry if flagged, and auto-pause the bot on URGENT
        if flag:
            alert_terry(flag, contact_name, inbound_message, reply_text)
            if flag == "URGENT":
                # A human is about to take this over — silence the bot for this contact
                pause_bot_for_contact(contact_id)

        print(f"Bot replied to {contact_name}: {reply_text}")
        if flag:
            print(f"Flagged for Terry: {flag}")

        return jsonify({"status": "ok", "reply": reply_text, "flagged": flag})
