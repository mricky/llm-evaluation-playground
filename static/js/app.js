/**
 * LLM Evaluation Arena & FACTS Studio Frontend Controller
 */

// State
let selectedWinner = 'tie';
let currentTrainerCase = null;
let benchmarkCases = [];

const RUBRIC_WEIGHTS = {
  factual_accuracy: 0.30,
  adherence: 0.25,
  completeness: 0.20,
  tone: 0.10,
  structure: 0.15
};

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initSliders();
  initWinnerButtons();
  initArenaRun();
  initSaveEvaluation();
  initTrainerMode();
  initHistoryTab();
});

// Toast notification helper
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.innerText = message;
  toast.style.borderColor = type === 'error' ? 'var(--danger)' : 'var(--primary)';
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

// Tab navigation
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      const target = btn.dataset.tab;
      document.getElementById(`${target}-tab`).classList.add('active');

      if (target === 'history') loadHistory();
      if (target === 'trainer' && benchmarkCases.length === 0) loadBenchmarks();
    });
  });
}

// FACTS Rubric Sliders & Real-Time Calculation
function initSliders() {
  const sliders = document.querySelectorAll('.facts-slider');
  sliders.forEach(slider => {
    slider.addEventListener('input', (e) => {
      const model = e.target.dataset.model;
      const dim = e.target.dataset.dim;
      const val = parseInt(e.target.value);
      
      document.getElementById(`val-${model}-${dim}`).innerText = `${val} / 5`;
      recalculateScore(model);
    });
  });
}

function recalculateScore(model) {
  let composite = 0.0;
  for (const [dim, weight] of Object.entries(RUBRIC_WEIGHTS)) {
    const val = parseInt(document.querySelector(`.facts-slider[data-model="${model}"][data-dim="${dim}"]`).value);
    // Convert 1-5 to 20-100%
    const normalized = val * 20.0;
    composite += (normalized * weight);
  }
  document.getElementById(`composite-score-${model}`).innerText = `Score: ${composite.toFixed(1)}%`;
}

function getAssessmentData(model) {
  const data = {};
  for (const dim of Object.keys(RUBRIC_WEIGHTS)) {
    const val = parseInt(document.querySelector(`.facts-slider[data-model="${model}"][data-dim="${dim}"]`).value);
    data[dim] = { score: val, notes: "" };
  }
  return data;
}

// Winner selector buttons
function initWinnerButtons() {
  const btns = document.querySelectorAll('.winner-btn');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedWinner = btn.dataset.winner;
    });
  });
}

// Run Concurrent Comparison
function initArenaRun() {
  const runBtn = document.getElementById('run-compare-btn');
  const promptInput = document.getElementById('prompt-input');

  runBtn.addEventListener('click', async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      showToast('Please enter a prompt first!', 'error');
      return;
    }

    const modelA = document.getElementById('model-a-select').value;
    const modelB = document.getElementById('model-b-select').value;

    document.getElementById('display-model-a-title').innerText = modelA;
    document.getElementById('display-model-b-title').innerText = modelB;
    
    document.getElementById('output-model-a').innerText = 'Generating local inference...';
    document.getElementById('output-model-b').innerText = 'Generating cloud inference...';
    document.getElementById('stat-latency-a').innerText = 'Latency: ...';
    document.getElementById('stat-latency-b').innerText = 'Latency: ...';

    runBtn.disabled = true;
    runBtn.innerText = '⏳ Running Parallel Inferences...';

    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model_a: modelA, model_b: modelB })
      });
      const data = await res.json();

      // Render Model A
      if (data.model_a.status === 'success') {
        document.getElementById('output-model-a').innerText = data.model_a.text;
        document.getElementById('stat-latency-a').innerText = `${data.model_a.latency_ms} ms`;
        document.getElementById('stat-words-a').innerText = `Tokens: ${data.model_a.tokens_or_words}`;
      } else {
        document.getElementById('output-model-a').innerText = `Error: ${data.model_a.error || 'Failed'}`;
      }

      // Render Model B
      if (data.model_b.status === 'success' || data.model_b.status === 'mock_success') {
        document.getElementById('output-model-b').innerText = data.model_b.text;
        document.getElementById('stat-latency-b').innerText = `${data.model_b.latency_ms} ms`;
        document.getElementById('stat-words-b').innerText = `Tokens: ${data.model_b.tokens_or_words}`;
      } else {
        document.getElementById('output-model-b').innerText = `Error: ${data.model_b.error || 'Failed'}`;
      }

      showToast('Models compared successfully!');
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    } finally {
      runBtn.disabled = false;
      runBtn.innerText = '⚡ Run Concurrent Comparison';
    }
  });
}

// Save Evaluation
function initSaveEvaluation() {
  const saveBtn = document.getElementById('save-eval-btn');
  saveBtn.addEventListener('click', async () => {
    const prompt = document.getElementById('prompt-input').value.trim();
    const modelA = document.getElementById('model-a-select').value;
    const modelB = document.getElementById('model-b-select').value;
    const respA = document.getElementById('output-model-a').innerText;
    const respB = document.getElementById('output-model-b').innerText;

    if (!prompt || respA.startsWith('Awaiting') || respB.startsWith('Awaiting')) {
      showToast('Run an inference before saving evaluation!', 'error');
      return;
    }

    const payload = {
      prompt,
      model_a_name: modelA,
      model_a_response: respA,
      model_b_name: modelB,
      model_b_response: respB,
      assessment_a: getAssessmentData('a'),
      assessment_b: getAssessmentData('b'),
      winner: selectedWinner,
      tags: ['arena', 'manual-eval']
    };

    saveBtn.disabled = true;
    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'success') {
        showToast(`Saved to audit log! Record ID: #${data.evaluation_id}`);
      }
    } catch (err) {
      showToast(`Save error: ${err.message}`, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });
}

// Evaluator Trainer (Quiz Mode)
async function loadBenchmarks() {
  const select = document.getElementById('trainer-case-select');
  select.innerHTML = '<option value="">-- Choose a benchmark challenge --</option>';

  try {
    const res = await fetch('/api/benchmarks');
    benchmarkCases = await res.json();
    benchmarkCases.forEach(b => {
      const opt = document.createElement('option');
      opt.value = b.id;
      opt.innerText = `[${b.domain}] ${b.title} (${b.difficulty})`;
      select.appendChild(opt);
    });
  } catch (err) {
    showToast('Failed to load benchmark challenges.', 'error');
  }
}

function initTrainerMode() {
  const select = document.getElementById('trainer-case-select');
  const workspace = document.getElementById('trainer-workspace');
  const submitBtn = document.getElementById('submit-trainer-btn');

  select.addEventListener('change', (e) => {
    const id = e.target.value;
    if (!id) {
      workspace.style.display = 'none';
      return;
    }

    currentTrainerCase = benchmarkCases.find(b => b.id === id);
    if (!currentTrainerCase) return;

    document.getElementById('trainer-domain').innerText = currentTrainerCase.domain;
    document.getElementById('trainer-difficulty').innerText = currentTrainerCase.difficulty;
    document.getElementById('trainer-case-title').innerText = currentTrainerCase.title;
    document.getElementById('trainer-prompt-text').innerText = currentTrainerCase.prompt;

    document.getElementById('trainer-model-a-name').innerText = currentTrainerCase.model_a_name;
    document.getElementById('trainer-model-a-resp').innerText = currentTrainerCase.model_a_response;

    document.getElementById('trainer-model-b-name').innerText = currentTrainerCase.model_b_name;
    document.getElementById('trainer-model-b-resp').innerText = currentTrainerCase.model_b_response;

    document.getElementById('trainer-results-card').style.display = 'none';
    workspace.style.display = 'block';
  });

  submitBtn.addEventListener('click', async () => {
    if (!currentTrainerCase) return;

    submitBtn.disabled = true;
    submitBtn.innerText = 'Calibrating against Gold Standard...';

    try {
      const payload = {
        case_id: currentTrainerCase.id,
        assessment_a: getAssessmentData('a'),
        assessment_b: getAssessmentData('b'),
        user_winner: selectedWinner
      };

      const res = await fetch('/api/trainer/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      // Render Results
      document.getElementById('res-alignment-val').innerText = `${data.overall_alignment_score}%`;
      document.getElementById('res-verdict-title').innerText = data.model_a_report.evaluation_verdict;
      document.getElementById('res-expert-explanation').innerText = data.expert_explanation;

      // Render Traps Caught
      const trapsList = document.getElementById('res-traps-list');
      trapsList.innerHTML = '';
      const allTraps = [
        ...data.model_a_report.traps_caught,
        ...data.model_b_report.traps_caught
      ];
      if (allTraps.length === 0) {
        trapsList.innerHTML = '<li style="color: var(--text-muted)">No hidden traps were spotted.</li>';
      } else {
        allTraps.forEach(t => {
          const li = document.createElement('li');
          li.innerText = t;
          trapsList.appendChild(li);
        });
      }

      // Render Critiques
      const critList = document.getElementById('res-critiques-list');
      critList.innerHTML = '';
      const allCritiques = [
        ...data.model_a_report.critique_notes,
        ...data.model_b_report.critique_notes
      ];
      if (allCritiques.length === 0) {
        critList.innerHTML = '<li style="color: var(--success)">Flawless precision! Your scores matched expert ratings.</li>';
      } else {
        allCritiques.forEach(c => {
          const li = document.createElement('li');
          li.innerText = c;
          critList.appendChild(li);
        });
      }

      document.getElementById('trainer-results-card').style.display = 'block';
      showToast('Evaluator calibration complete!');
    } catch (err) {
      showToast(`Submission error: ${err.message}`, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = '🔍 Reveal Gold Standard & Grade My Precision';
    }
  });
}

// History
async function loadHistory() {
  const tbody = document.getElementById('history-table-body');
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    tbody.innerHTML = '';

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No evaluations saved yet.</td></tr>';
      return;
    }

    data.forEach(row => {
      const tr = document.createElement('tr');
      const timeStr = new Date(row.created_at).toLocaleString();
      tr.innerHTML = `
        <td>#${row.id}</td>
        <td>${timeStr}</td>
        <td><strong>${row.model_a_name}</strong></td>
        <td><span class="score-pill">${row.score_a}%</span></td>
        <td><strong>${row.model_b_name}</strong></td>
        <td><span class="score-pill">${row.score_b}%</span></td>
        <td><span class="model-badge ${row.winner === 'tie' ? '' : 'cloud'}">${row.winner.toUpperCase()}</span></td>
        <td style="color: var(--text-muted); font-size: 12px;">${row.prompt.substring(0, 40)}...</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color: var(--danger)">Error loading history: ${err.message}</td></tr>`;
  }
}

function initHistoryTab() {
  document.getElementById('refresh-history-btn').addEventListener('click', loadHistory);
}
