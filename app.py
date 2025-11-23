from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import random
import time

app = Flask(__name__)
# Enable CORS so your React frontend can talk to this Flask backend
CORS(app) 

# --- In-Memory Database (Replaced by SQLite/Postgres in production) ---
# For a simple experiment hosted on Railway, in-memory works 
# as long as the server doesn't restart during the session.
STATE = {
    "status": "LOBBY", # LOBBY, TREATMENT_1, TREATMENT_2, FINISHED
    "round": 0,
    "sub_round": 1,
    "treatment": 1,
    "pairings": {} # { "pair_0": {"p1": "uid1", "p2": "uid2"} }
}

PLAYERS = {} # { "uid": {"name": "Alice", "role": "PARTICIPANT", "earnings": 0} }
GAMES = {}   # { "game_id": { "proposer": "...", "responder": "...", "offer": 10, "status": "..." } }

ENDOWMENT = 10

# --- Helper Functions ---
def get_role_info(uid, sub_round):
    # Find pair
    my_pair = None
    for pid, pair in STATE["pairings"].items():
        if pair["p1"] == uid or pair["p2"] == uid:
            my_pair = pair
            break
    
    if not my_pair:
        return {"role": "SPECTATOR", "partner_name": None, "partner_id": None}
    
    is_p1 = (uid == my_pair["p1"])
    # Logic: P1 is proposer for rounds 1-2, P2 for 3-4
    is_proposer = (sub_round <= 2 and is_p1) or (sub_round > 2 and not is_p1)
    
    partner_id = my_pair["p2"] if is_p1 else my_pair["p1"]
    partner_name = PLAYERS.get(partner_id, {}).get("name", "Unknown")
    
    return {
        "role": "PROPOSER" if is_proposer else "RESPONDER",
        "partner_id": partner_id,
        "partner_name": partner_name
    }

# --- Routes ---

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "msg": "Ultimatum Game API Active"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    uid = data.get('uid')
    name = data.get('name')
    is_researcher = data.get('isResearcher', False)
    
    if not uid:
        return jsonify({"error": "No UID provided"}), 400
        
    PLAYERS[uid] = {
        "uid": uid,
        "name": name,
        "role": "RESEARCHER" if is_researcher else "PARTICIPANT",
        "earnings": 0,
        "joined_at": time.time()
    }
    return jsonify({"success": True, "player": PLAYERS[uid]})

@app.route('/state', methods=['GET'])
def get_state():
    # Polling endpoint: Returns global state + player specific context
    uid = request.args.get('uid')
    
    if not uid or uid not in PLAYERS:
        return jsonify({"error": "Player not found"}), 404

    # Get my specific game if active
    my_game_data = None
    
    # Identify the current game ID for this user
    role_info = get_role_info(uid, STATE["sub_round"])
    partner_id = role_info.get('partner_id')
    
    if partner_id:
        # Deterministic Game ID based on sorted IDs to ensure both players look at same game
        p1 = uid if uid < partner_id else partner_id
        p2 = partner_id if uid < partner_id else uid
        game_id = f"{STATE['treatment']}_{STATE['sub_round']}_{p1}_{p2}"
        
        if game_id in GAMES:
            my_game_data = GAMES[game_id]
        else:
            # Lazy creation of game state if not exists
            if role_info['role'] == 'PROPOSER':
                GAMES[game_id] = {
                    "id": game_id,
                    "proposer": uid,
                    "responder": partner_id,
                    "offer": None,
                    "status": "WAITING_OFFER",
                    "earnings": {}
                }
                my_game_data = GAMES[game_id]

    return jsonify({
        "global": STATE,
        "me": PLAYERS[uid],
        "my_game": my_game_data,
        "role_info": role_info,
        "all_players_count": len(PLAYERS)
    })

# --- Researcher Controls ---

@app.route('/admin/start_treatment', methods=['POST'])
def start_treatment():
    data = request.json
    treatment = data.get('treatment')
    
    participant_ids = [p['uid'] for p in PLAYERS.values() if p['role'] != 'RESEARCHER']
    random.shuffle(participant_ids)
    
    new_pairings = {}
    for i in range(0, len(participant_ids), 2):
        if i + 1 < len(participant_ids):
            new_pairings[f"pair_{i//2}"] = {
                "p1": participant_ids[i],
                "p2": participant_ids[i+1]
            }
            
    STATE["status"] = f"TREATMENT_{treatment}"
    STATE["treatment"] = treatment
    STATE["sub_round"] = 1
    STATE["pairings"] = new_pairings
    
    return jsonify({"success": True, "state": STATE})

@app.route('/admin/next_round', methods=['POST'])
def next_round():
    if STATE["sub_round"] < 4:
        STATE["sub_round"] += 1
    else:
        STATE["status"] = "WAITING_NEXT_PHASE"
        
    return jsonify({"success": True, "state": STATE})

# --- Game Actions ---

@app.route('/game/offer', methods=['POST'])
def make_offer():
    data = request.json
    game_id = data.get('game_id')
    amount = data.get('amount')
    
    if game_id in GAMES:
        GAMES[game_id]['offer'] = amount
        GAMES[game_id]['status'] = 'OFFER_MADE'
        return jsonify({"success": True})
    return jsonify({"error": "Game not found"}), 404

@app.route('/game/respond', methods=['POST'])
def respond_offer():
    data = request.json
    game_id = data.get('game_id')
    accepted = data.get('accepted')
    
    if game_id in GAMES:
        game = GAMES[game_id]
        offer = game['offer']
        
        prop_earn = (ENDOWMENT - offer) if accepted else 0
        resp_earn = offer if accepted else 0
        
        game['response'] = 'ACCEPTED' if accepted else 'REJECTED'
        game['status'] = 'COMPLETED'
        game['earnings'] = {
            game['proposer']: prop_earn,
            game['responder']: resp_earn
        }
        
        # Update cumulative earnings
        if game['proposer'] in PLAYERS: PLAYERS[game['proposer']]['earnings'] += prop_earn
        if game['responder'] in PLAYERS: PLAYERS[game['responder']]['earnings'] += resp_earn
        
        return jsonify({"success": True})
    return jsonify({"error": "Game not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
