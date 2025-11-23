from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import random
import time

app = Flask(__name__)
CORS(app) 

# --- Global Storage ---
STATE = {
    "status": "LOBBY", 
    "round": 0,
    "sub_round": 1,
    "treatment": 1,
    "pairings": {}
}

PLAYERS = {} 
GAMES = {}   

ENDOWMENT = 10

# --- Helper: Create Games Immediately ---
def create_games_for_current_round():
    """
    Generates game objects for all pairs for the current treatment/round
    immediately.
    """
    t = STATE["treatment"]
    r = STATE["sub_round"]
    
    for pair_id, pair in STATE["pairings"].items():
        p1 = pair["p1"]
        p2 = pair["p2"]
        
        # Logic: P1 is proposer for rounds 1-2, P2 for 3-4
        is_p1_proposer = (r <= 2)
        
        proposer = p1 if is_p1_proposer else p2
        responder = p2 if is_p1_proposer else p1
        
        # Unique ID based on sorted PIDs to ensure consistency
        id_a = p1 if p1 < p2 else p2
        id_b = p2 if p1 < p2 else p1
        game_id = f"{t}_{r}_{id_a}_{id_b}"
        
        if game_id not in GAMES:
            GAMES[game_id] = {
                "id": game_id,
                "treatment": t,
                "round": r,
                "proposer": proposer,
                "responder": responder,
                "offer": None,
                "status": "WAITING_OFFER",
                "earnings": {},
                "created_at": time.time() # Added for sorting
            }
            print(f"Created game {game_id}")

def get_role_info(uid, sub_round):
    my_pair = None
    for pid, pair in STATE["pairings"].items():
        if pair["p1"] == uid or pair["p2"] == uid:
            my_pair = pair
            break
    
    if not my_pair:
        return {"role": "SPECTATOR", "partner_name": None, "partner_id": None}
    
    is_p1 = (uid == my_pair["p1"])
    is_proposer = (sub_round <= 2 and is_p1) or (sub_round > 2 and not is_p1)
    
    partner_id = my_pair["p2"] if is_p1 else my_pair["p1"]
    partner_name = PLAYERS.get(partner_id, {}).get("name", "Unknown")
    
    return {
        "role": "PROPOSER" if is_proposer else "RESPONDER",
        "partner_id": partner_id,
        "partner_name": partner_name
    }

# --- Standard Routes ---

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "msg": "Ultimatum Game API Active"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    uid = data.get('uid')
    name = data.get('name')
    
    if not uid: return jsonify({"error": "No UID"}), 400

    if uid in PLAYERS:
        return jsonify({"success": True, "player": PLAYERS[uid]})

    if len(PLAYERS) < 3:
        role = "RESEARCHER"
    else:
        role = "PARTICIPANT"
        
    PLAYERS[uid] = {
        "uid": uid,
        "name": name,
        "role": role,
        "earnings": 0,
        "joined_at": time.time()
    }
    
    return jsonify({"success": True, "player": PLAYERS[uid]})

@app.route('/state', methods=['GET'])
def get_state():
    uid = request.args.get('uid')
    if not uid or uid not in PLAYERS: return jsonify({"error": "Player not found"}), 404

    role_info = get_role_info(uid, STATE["sub_round"])
    partner_id = role_info.get('partner_id')
    my_game_data = None
    
    if partner_id:
        p1 = uid if uid < partner_id else partner_id
        p2 = partner_id if uid < partner_id else uid
        game_id = f"{STATE['treatment']}_{STATE['sub_round']}_{p1}_{p2}"
        
        # Direct lookup (No lazy creation anymore)
        if game_id in GAMES:
            my_game_data = GAMES[game_id]

    return jsonify({
        "global": STATE,
        "me": PLAYERS[uid],
        "my_game": my_game_data,
        "role_info": role_info,
        "all_players_count": len(PLAYERS)
    })

# --- DATA MANAGEMENT ---

@app.route('/export_data', methods=['GET'])
def export_data():
    return jsonify({
        "all_players": PLAYERS,
        "all_games": GAMES,
        "final_state": STATE
    })

@app.route('/reset_server', methods=['POST'])
def reset_server():
    global PLAYERS, GAMES, STATE
    PLAYERS = {}
    GAMES = {}
    STATE = {
        "status": "LOBBY",
        "round": 0,
        "sub_round": 1,
        "treatment": 1,
        "pairings": {}
    }
    return jsonify({"success": True, "message": "Server wiped."})


# --- Game Control (Researcher) ---

@app.route('/admin/start_treatment', methods=['POST'])
def start_treatment():
    data = request.json
    treatment = data.get('treatment')
    
    ids = [p['uid'] for p in PLAYERS.values() if p['role'] != 'RESEARCHER']
    random.shuffle(ids)
    
    pairs = {}
    for i in range(0, len(ids), 2):
        if i + 1 < len(ids):
            pairs[f"pair_{i//2}"] = {
                "p1": ids[i],
                "p2": ids[i+1]
            }
            
    STATE["status"] = f"TREATMENT_{treatment}"
    STATE["treatment"] = treatment
    STATE["sub_round"] = 1
    STATE["pairings"] = pairs
    
    # EAGERLY CREATE ROUND 1 GAMES
    create_games_for_current_round()
    
    return jsonify({"success": True})

@app.route('/admin/next_round', methods=['POST'])
def next_round():
    if STATE["sub_round"] < 4:
        STATE["sub_round"] += 1
        # EAGERLY CREATE GAMES FOR NEW ROUND
        create_games_for_current_round()
    else:
        STATE["status"] = "WAITING_NEXT_PHASE"
        
    return jsonify({"success": True})

# --- Gameplay (Participants) ---

@app.route('/game/offer', methods=['POST'])
def make_offer():
    data = request.json
    gid = data.get('game_id')
    amount = data.get('amount')
    
    if gid in GAMES:
        GAMES[gid]['offer'] = amount
        GAMES[gid]['status'] = 'OFFER_MADE'
        return jsonify({"success": True})
    return jsonify({"error": "No game"}), 404

@app.route('/game/respond', methods=['POST'])
def respond_offer():
    data = request.json
    gid = data.get('game_id')
    accepted = data.get('accepted')
    
    if gid in GAMES:
        g = GAMES[gid]
        offer = g['offer']
        p_earn = (ENDOWMENT - offer) if accepted else 0
        r_earn = offer if accepted else 0
        
        g['response'] = 'ACCEPTED' if accepted else 'REJECTED'
        g['status'] = 'COMPLETED'
        g['earnings'] = {g['proposer']: p_earn, g['responder']: r_earn}
        
        if g['proposer'] in PLAYERS: PLAYERS[g['proposer']]['earnings'] += p_earn
        if g['responder'] in PLAYERS: PLAYERS[g['responder']]['earnings'] += r_earn
        
        return jsonify({"success": True})
    return jsonify({"error": "No game"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
