import React, { useState, useEffect } from 'react';
import { User as UserIcon, Eye, EyeOff, Shield, Database, Play, RotateCcw, CheckCircle } from 'lucide-react';

// ==========================================
// IMPORTANT: PASTE YOUR RAILWAY URL HERE
// Example: "https://ultimatum-production.up.railway.app"
// ==========================================
const API_URL = "https://ultimatum-production.up.railway.app"; 

const ENDOWMENT = 10;

const GameApp = () => {
  const [userId, setUserId] = useState(null);
  const [userName, setUserName] = useState('');
  const [isResearcher, setIsResearcher] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // App State (Matches Python Backend)
  const [gameState, setGameState] = useState({
    status: 'LOBBY',
    round: 0,
    sub_round: 1,
    treatment: 1,
    pairings: {}
  });
  
  const [myGame, setMyGame] = useState(null);
  const [myPlayerInfo, setMyPlayerInfo] = useState(null);
  const [roleInfo, setRoleInfo] = useState({});
  const [playerCount, setPlayerCount] = useState(0);

  // --- 1. Polling System (The Heartbeat) ---
  // This replaces Firebase onSnapshot. It asks Python for data every 1 second.
  useEffect(() => {
    if (!userId) return;

    const fetchData = async () => {
      try {
        const response = await fetch(`${API_URL}/state?uid=${userId}`);
        if (response.ok) {
          const data = await response.json();
          setGameState(data.global);
          setMyPlayerInfo(data.me);
          setMyGame(data.my_game);
          setRoleInfo(data.role_info);
          setPlayerCount(data.all_players_count);
        }
      } catch (error) {
        console.error("Connection error:", error);
      }
    };

    // Poll immediately, then every 1000ms
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, [userId]);


  // --- 2. Actions (Sending data to Python) ---

  const registerUser = async () => {
    if (!userName.trim()) return;
    setLoading(true);

    // Generate a random ID for the session
    const newUid = crypto.randomUUID();

    try {
      const res = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: newUid,
          name: userName,
          isResearcher: isResearcher
        })
      });

      if (res.ok) {
        setUserId(newUid);
      } else {
        alert("Failed to join server. Check URL.");
      }
    } catch (e) {
      alert("Error connecting to Railway server.");
    }
    setLoading(false);
  };

  const handleResearcherAction = async (action) => {
    let endpoint = '';
    let body = {};

    if (action === 'START_T1') {
      endpoint = '/admin/start_treatment';
      body = { treatment: 1 };
    } else if (action === 'START_T2') {
      endpoint = '/admin/start_treatment';
      body = { treatment: 2 };
    } else if (action === 'NEXT_ROUND') {
      endpoint = '/admin/next_round';
    }

    await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  };

  const makeOffer = async (amount) => {
    if (!myGame) return;
    await fetch(`${API_URL}/game/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: myGame.id, amount: amount })
    });
  };

  const respondToOffer = async (accepted) => {
    if (!myGame) return;
    await fetch(`${API_URL}/game/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: myGame.id, accepted: accepted })
    });
  };


  // --- 3. Views (UI) ---

  // A. Registration
  if (!userId) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 p-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg border border-slate-200">
          <div className="mb-6 flex items-center justify-center">
            <Database className="h-10 w-10 text-blue-600" />
          </div>
          <h1 className="mb-2 text-center text-2xl font-bold text-slate-800">Ultimatum Game</h1>
          <p className="mb-6 text-center text-slate-500">Enter your name to join the server.</p>
          
          <input
            type="text"
            placeholder="Full Name"
            className="mb-4 w-full rounded-lg border border-slate-300 p-3 outline-none focus:border-blue-500"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
          />
          
          <label className="mb-6 flex items-center gap-2 text-sm text-slate-600">
            <input 
              type="checkbox" 
              checked={isResearcher} 
              onChange={(e) => setIsResearcher(e.target.checked)}
            />
            I am the Researcher (Admin)
          </label>

          <button
            onClick={registerUser}
            disabled={!userName || loading}
            className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Join Experiment"}
          </button>
          
          {API_URL === "INSERT_YOUR_RAILWAY_URL_HERE" && (
            <p className="mt-4 text-center text-xs text-red-500 font-bold">
              ⚠️ Warning: You haven't set the API_URL in the code yet!
            </p>
          )}
        </div>
      </div>
    );
  }

  // B. Researcher Dashboard
  if (myPlayerInfo?.role === 'RESEARCHER') {
    return (
      <div className="min-h-screen bg-slate-100 p-6">
        <header className="mb-8 flex items-center justify-between rounded-xl bg-white p-6 shadow-sm">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Researcher Dashboard</h1>
            <p className="text-slate-500">Connected to Python Backend</p>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold text-slate-600">Participants: {playerCount}</div>
            <div className="text-xs text-slate-400">Status: {gameState.status}</div>
          </div>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Controls */}
          <div className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-bold text-slate-800 flex items-center gap-2">
              <Play className="h-5 w-5" /> Controls
            </h2>
            <div className="space-y-4">
               <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                 <button 
                  onClick={() => handleResearcherAction('START_T1')}
                  disabled={gameState.status === 'TREATMENT_1'}
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                 >
                   Start Treatment 1 (Anonymous)
                 </button>
               </div>
               <div className="rounded-lg border border-purple-100 bg-purple-50 p-4">
                 <button 
                  onClick={() => handleResearcherAction('START_T2')}
                  disabled={gameState.status === 'TREATMENT_2'}
                  className="rounded bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-50"
                 >
                   Start Treatment 2 (Known)
                 </button>
               </div>
               <div className="border-t pt-4">
                 <p className="mb-2 text-sm font-medium">Round: {gameState.sub_round} / 4</p>
                 <button 
                  onClick={() => handleResearcherAction('NEXT_ROUND')}
                  className="w-full rounded bg-slate-800 px-4 py-2 text-white hover:bg-slate-900"
                 >
                   Next Round
                 </button>
               </div>
            </div>
          </div>

          {/* Monitoring */}
          <div className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-bold text-slate-800 flex items-center gap-2">
              <Eye className="h-5 w-5" /> Pairings
            </h2>
            <div className="max-h-[400px] overflow-y-auto space-y-2">
               {gameState.pairings && Object.entries(gameState.pairings).map(([key, pair]) => (
                 <div key={key} className="flex justify-between border p-2 rounded text-sm">
                    <span>{pair.p1.slice(0,5)}...</span>
                    <span className="font-bold">VS</span>
                    <span>{pair.p2.slice(0,5)}...</span>
                 </div>
               ))}
               {!gameState.pairings && <p className="text-slate-400">No pairings yet.</p>}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // C. Lobby
  if (gameState.status === 'LOBBY' || gameState.status === 'WAITING_NEXT_PHASE') {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-slate-50 text-center">
        <div className="animate-pulse rounded-full bg-blue-100 p-6">
          <RotateCcw className="h-10 w-10 text-blue-600" />
        </div>
        <h2 className="mt-6 text-xl font-bold text-slate-800">Waiting for Researcher...</h2>
        <p className="mt-8 rounded-full bg-slate-200 px-4 py-1 text-xs text-slate-500">Your ID: {userId}</p>
      </div>
    );
  }

  // D. Active Game
  const role = roleInfo?.role;
  const partnerName = roleInfo?.partner_name;
  
  const displayName = gameState.treatment === 1 ? "Anonymous Partner" : partnerName;
  const displayIcon = gameState.treatment === 1 ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />;

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <div className="bg-white p-4 shadow-sm">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div>
            <span className="rounded bg-blue-100 px-2 py-1 text-xs font-bold text-blue-800">Treatment {gameState.treatment}</span>
            <span className="ml-2 text-sm text-slate-600">Round {gameState.sub_round}</span>
          </div>
          <div className="font-semibold text-slate-700">{userName} (You)</div>
        </div>
      </div>

      <main className="mx-auto mt-8 w-full max-w-xl px-4">
        {/* Partner Card */}
        <div className="mb-6 overflow-hidden rounded-xl bg-white shadow-sm border border-slate-200">
           <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
             <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Opponent</span>
             <span className="text-slate-400">{displayIcon}</span>
           </div>
           <div className="p-6 text-center">
             <div className="text-2xl font-bold text-slate-800">{displayName}</div>
           </div>
        </div>

        {/* Game Logic */}
        <div className="rounded-xl bg-white p-8 shadow-lg">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-slate-800">${ENDOWMENT}</h2>
            <p className="text-slate-500">Total Pot</p>
          </div>

          {!myGame ? (
             <div className="text-center text-slate-500">Loading round...</div>
          ) : (
            <>
              {role === 'PROPOSER' && (
                <>
                  <h3 className="mb-4 text-xl font-semibold text-blue-600">You are the Proposer</h3>
                  {myGame.status === 'WAITING_OFFER' && (
                    <div className="grid grid-cols-5 gap-2">
                       {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((amt) => (
                         <button key={amt} onClick={() => makeOffer(amt)} className="rounded bg-blue-50 py-3 font-bold text-blue-600 hover:bg-blue-600 hover:text-white">
                           ${amt}
                         </button>
                       ))}
                    </div>
                  )}
                  {myGame.status === 'OFFER_MADE' && (
                    <div className="rounded bg-yellow-50 p-4 text-center text-yellow-800">
                      Waiting for partner response to ${myGame.offer}...
                    </div>
                  )}
                </>
              )}

              {role === 'RESPONDER' && (
                <>
                  <h3 className="mb-4 text-xl font-semibold text-purple-600">You are the Responder</h3>
                  {myGame.status === 'WAITING_OFFER' && <p className="text-center text-slate-500">Waiting for offer...</p>}
                  {myGame.status === 'OFFER_MADE' && (
                    <div className="text-center">
                      <div className="mb-6 text-4xl font-bold text-green-600">${myGame.offer}</div>
                      <div className="grid grid-cols-2 gap-4">
                        <button onClick={() => respondToOffer(true)} className="rounded-xl bg-green-600 py-4 font-bold text-white">Accept</button>
                        <button onClick={() => respondToOffer(false)} className="rounded-xl bg-red-500 py-4 font-bold text-white">Reject</button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {myGame.status === 'COMPLETED' && (
                 <div className="text-center mt-4 p-4 bg-slate-50 rounded">
                    <p className="font-bold text-lg">{myGame.response}</p>
                    <p>You earned: ${myGame.earnings[userId]}</p>
                 </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default GameApp;