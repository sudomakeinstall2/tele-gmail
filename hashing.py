import hmac

key = ""
with open('secret_key.txt') as f:
    key = f.read().strip()

#### hasing
def hash_str(s):
    return hmac.new(key, s).hexdigest()
    
def make_secure(s):
    return "%s|%s"%(s, hash_str(s))
    
def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure(val):
        return val
    return None
#### end hashing
