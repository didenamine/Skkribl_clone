#The format is Type : content 
# message parts can be: NAME, DRAW, CLEAR, CHAT, NEW_ROUND, SECRET, HINT, TIME  
#NAME : the client name 
#DRAW : the drawing coordinates
#CLEAR : the clear canvas message
#CHAT : the chat message
#NEW_ROUND : the new round message
#SECRET : the secret word message
#HINT : the hint message
#TIME : the time message




def make_msg(msg_type, content=""):
    return f"{msg_type}:{content}\n"

def parse_msg(msg_string):
    """Returns (type, content) or (None, None) can be fixed to something else later ... i ll just stick with this now """
    if ":" in msg_string:
        parts = msg_string.split(":", 1)
        return parts[0], parts[1]
    return None, None

