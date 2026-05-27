"""
Pirate speak coning effect.
"""

import re
import random


def transform_pirate(text: str) -> str:
    """Transform text into pirate speak."""
    # 1. Pronoun Hijacking
    pronouns = {
        r"\bmy\b": "me", r"\bMy\b": "Me",
        r"\bmine\b": "me own", r"\bMine\b": "Me own",
        r"\byour\b": "yer", r"\bYour\b": "Yer",
        r"\byours\b": "yers", r"\bYours\b": "Yers",
        r"\byou\b": "ye", r"\bYou\b": "Ye",
        r"\bthem\b": "'em", r"\bThem\b": "'em",
    }
    for pattern, replacement in pronouns.items():
        text = re.sub(pattern, replacement, text)

    # 2. Verb Conjugation Flattening
    verbs = {
        r"\bam\b": "be", r"\bAm\b": "Be",
        r"\bis\b": "be", r"\bIs\b": "Be",
        r"\bare\b": "be", r"\bAre\b": "Be",
        r"\bwas\b": "be", r"\bWas\b": "Be",
        r"\bwere\b": "be", r"\bWere\b": "Be",
    }
    for pattern, replacement in verbs.items():
        text = re.sub(pattern, replacement, text)

    # 3. Massive Conversational Translation Dictionary
    vocab = {
        r"\b(house|home|room|place)\b": "quarters",
        r"\b(House|Home|Room|Place)\b": "Quarters",
        r"\b(food|dinner|meal|eat)\b": "grub",
        r"\b(Food|Dinner|Meal|Eat)\b": "Grub",
        r"\b(water|drink)\b": "grog",
        r"\b(Water|Drink)\b": "Grog",
        r"\b(man|guy|boy|people|person)\b": "lad",
        r"\b(Man|Guy|Boy|People|Person)\b": "Lad",
        r"\b(woman|girl)\b": "lass",
        r"\b(Woman|Girl)\b": "Lass",
        r"\b(money|cash|gold)\b": "booty",
        r"\b(Money|Cash|Gold)\b": "Booty",
        r"\b(friend|buddy|bro)\b": "matey",
        r"\b(Friend|Buddy|Bro)\b": "Matey",
        r"\b(problem|trouble|issue)\b": "squall",
        r"\b(Problem|Trouble|Issue)\b": "Squall",
        r"\b(mistake|error)\b": "blunder",
        r"\b(Mistake|Error)\b": "Blunder",
        r"\bnight\b": "eventide",
        r"\bNight\b": "Eventide",
        r"\b(day|morning)\b": "morrow",
        r"\b(Day|Morning)\b": "Morrow",
        r"\b(want|need|desire)\b": "yearn fer",
        r"\b(Want|Need|Desire)\b": "Yearn fer",
        r"\b(understand|know|believe)\b": "savvy",
        r"\b(Understand|Know|Believe)\b": "Savvy",
        r"\b(say|tell|speak|talk)\b": "spin a yarn",
        r"\b(Say|Tell|Speak|Talk)\b": "Spin a yarn",
        r"\b(go|travel|walk|run)\b": "set sail",
        r"\b(Go|Travel|Walk|Run)\b": "Set sail",
        r"\b(look|see|watch|find)\b": "spy",
        r"\b(Look|See|Watch|Find)\b": "Spy",
        r"\b(fight|attack|kill|beat)\b": "scupper",
        r"\b(Fight|Attack|Kill|Beat)\b": "Scupper",
        r"\b(help|assist)\b": "lend a hand",
        r"\b(Help|Assist)\b": "Lend a hand",
        r"\b(love|like)\b": "prize",
        r"\b(Love|Like)\b": "Prize",
        r"\b(hate|dislike)\b": "loathe",
        r"\b(Hate|Dislike)\b": "Loathe",
        r"\b(good|great|cool)\b": "grand",
        r"\b(Good|Great|Cool)\b": "Grand",
        r"\b(bad|terrible|awful)\b": "foul",
        r"\b(Bad|Terrible|Awful)\b": "Foul",
        r"\b(scared|afraid)\b": "lily-livered",
        r"\b(Scared|Afraid)\b": "Lily-livered",
        r"\b(angry|mad)\b": "wrathful",
        r"\b(Angry|Mad)\b": "Wrathful",
        r"\byes\b": "aye", r"\bYes\b": "Aye",
        r"\bno\b": "nay", r"\bNo\b": "Nay",
        r"\bthere\b": "thar", r"\bThere\b": "Thar",
        r"\band\b": "an'", r"\bAnd\b": "an'",
        r"\bof\b": "o'", r"\bOf\b": "o'",
    }
    for pattern, replacement in vocab.items():
        text = re.sub(pattern, replacement, text)

    # 4. Phonetic Accent
    text = re.sub(r"\b(\w+)ing\b", r"\1in'", text)
    text = re.sub(r"\b(\w+)Ing\b", r"\1in'", text)

    # 5. Sentence Restructuring
    sentences = re.split(r"([.!?]+)", text)
    transformed_sentences = []
    exclamations = ["Arr!", "Avast ye!", "By the powers!", "Yo ho ho!", "Shiver me timbers!", "Ahoy!"]
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        if not sentence:
            continue
        if random.random() < 0.3:
            sentence = f"{random.choice(exclamations)} {sentence}"
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""
        transformed_sentences.append(sentence + punctuation)
        
    text = " ".join(transformed_sentences)
    text += random.choice([" arrr!", " ye scurvy dog!", " shiver me timbers!", " ahoy matey!"])
    return text
