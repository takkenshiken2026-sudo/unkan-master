/* unkan-master 過去問・実践演習・一問一答の静的ページ採点ロジック.

   data-quiz-type と data-quiz-correct を読み、フォーム選択値と比較する。
   採点まで .q-quiz-locked がついた要素（正答 / 解説）は非表示で、採点後に
   class が外れて表示される。

   対応型:
     - single           correct="3"
     - multi            correct="1,3"
     - combination      correct="A-2;B-3;C-5"   各サブ問題は name="q-A" 形式
     - truefalse_group  correct="適-2,3;不適-1,4"  各記述は name="q-stmt-1" 形式
*/
(function () {
  'use strict';

  function parseCombinationCorrect(raw) {
    var map = {};
    raw.split(';').forEach(function (p) {
      var idx = p.indexOf('-');
      if (idx <= 0) return;
      var k = p.slice(0, idx).trim();
      var v = p.slice(idx + 1).trim();
      if (k && v) map[k] = v;
    });
    return map;
  }

  function parseTruefalseCorrect(raw) {
    var map = {}; // { '1': '適', '2': '不適', ... }
    raw.split(';').forEach(function (g) {
      var idx = g.indexOf('-');
      if (idx <= 0) return;
      var label = g.slice(0, idx).trim();
      var nums = g.slice(idx + 1).trim();
      if (!label || !nums) return;
      nums.split(',').forEach(function (n) {
        n = n.trim();
        if (n) map[n] = label;
      });
    });
    return map;
  }

  function gradeSingle(form, correct) {
    var sel = form.querySelector('input[name="q-opt"]:checked');
    if (!sel) return { ok: null, msg: '選択肢を選んでください。' };
    var ok = String(sel.value) === String(correct);
    return { ok: ok, picked: [sel.value], correct: [correct] };
  }

  function gradeMulti(form, correct) {
    var correctList = correct.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    var picked = Array.prototype.slice.call(
      form.querySelectorAll('input[name="q-opt"]:checked')
    ).map(function (i) { return i.value; });
    if (picked.length === 0) return { ok: null, msg: '選択肢を1つ以上選んでください。' };
    var setA = new Set(correctList);
    var setB = new Set(picked);
    var ok = setA.size === setB.size && correctList.every(function (v) { return setB.has(v); });
    return { ok: ok, picked: picked.sort(), correct: correctList.sort() };
  }

  function gradeCombination(form, correct) {
    var expected = parseCombinationCorrect(correct);
    var got = {};
    var keys = Object.keys(expected);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      var sel = form.querySelector('input[name="q-' + cssEscape(k) + '"]:checked');
      if (!sel) return { ok: null, msg: k + ' の選択肢を選んでください。' };
      got[k] = sel.value;
    }
    var ok = keys.every(function (k) { return String(expected[k]) === String(got[k]); });
    return { ok: ok, picked: got, correct: expected, kind: 'combination' };
  }

  function gradeTrueFalse(form, correct) {
    var expected = parseTruefalseCorrect(correct);
    var got = {};
    var nums = Object.keys(expected);
    for (var i = 0; i < nums.length; i++) {
      var n = nums[i];
      var sel = form.querySelector('input[name="q-stmt-' + n + '"]:checked');
      if (!sel) return { ok: null, msg: '記述 ' + n + ' の判定を選んでください。' };
      got[n] = sel.value;
    }
    var ok = nums.every(function (n) { return expected[n] === got[n]; });
    return { ok: ok, picked: got, correct: expected, kind: 'truefalse' };
  }

  function cssEscape(s) {
    return s.replace(/[^a-zA-Z0-9_\-]/g, function (ch) {
      return '\\' + ch;
    });
  }

  function buildResultHtml(result, quizType) {
    if (result.ok === null) {
      return '<p class="q-grade-msg q-grade-msg--prompt">' + escapeHtml(result.msg) + '</p>';
    }
    var icon = result.ok ? '◯' : '✕';
    var label = result.ok ? '正解' : '不正解';
    var pickedText, correctText;
    if (quizType === 'combination') {
      pickedText = Object.keys(result.picked).map(function (k) {
        return k + '→' + result.picked[k];
      }).join(' ');
      correctText = Object.keys(result.correct).map(function (k) {
        return k + '→' + result.correct[k];
      }).join(' ');
    } else if (quizType === 'truefalse_group') {
      pickedText = Object.keys(result.picked).map(function (k) {
        return '記述' + k + '→' + result.picked[k];
      }).join(' / ');
      correctText = Object.keys(result.correct).map(function (k) {
        return '記述' + k + '→' + result.correct[k];
      }).join(' / ');
    } else if (quizType === 'multi') {
      pickedText = '（' + result.picked.join(', ') + '）';
      correctText = '（' + result.correct.join(', ') + '）';
    } else {
      pickedText = '（' + result.picked[0] + '）';
      correctText = '（' + result.correct[0] + '）';
    }
    var cls = result.ok ? 'q-grade-msg--ok' : 'q-grade-msg--ng';
    return (
      '<p class="q-grade-msg ' + cls + '">' +
      '<strong>' + icon + ' ' + label + '</strong></p>' +
      '<p class="q-grade-detail">あなたの解答：' + escapeHtml(pickedText) + '</p>' +
      '<p class="q-grade-detail">正答：' + escapeHtml(correctText) + '</p>' +
      '<p class="q-grade-detail">下に正答の根拠と解説を表示しました。</p>'
    );
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (m) {
      return {
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[m];
    });
  }

  function unlock(form) {
    document.querySelectorAll('.q-quiz-locked').forEach(function (el) {
      el.classList.remove('q-quiz-locked');
    });
    form.classList.add('q-quiz-graded');
  }

  function reset(form, resultEl) {
    form.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(function (i) {
      i.checked = false;
    });
    document.querySelectorAll('.q-quiz-relock').forEach(function (el) {
      el.classList.add('q-quiz-locked');
    });
    form.classList.remove('q-quiz-graded');
    if (resultEl) resultEl.innerHTML = '';
  }

  function init(form) {
    var quizType = form.getAttribute('data-quiz-type') || 'single';
    var correct = form.getAttribute('data-quiz-correct') || '';
    var resultEl = form.querySelector('.q-grade-result');
    var gradeBtn = form.querySelector('.q-grade-btn');
    var resetBtn = form.querySelector('.q-reset-btn');
    if (!gradeBtn || !resultEl) return;

    gradeBtn.addEventListener('click', function () {
      var result;
      if (quizType === 'multi') result = gradeMulti(form, correct);
      else if (quizType === 'combination') result = gradeCombination(form, correct);
      else if (quizType === 'truefalse_group') result = gradeTrueFalse(form, correct);
      else result = gradeSingle(form, correct);

      resultEl.innerHTML = buildResultHtml(result, quizType);
      if (result.ok !== null) unlock(form);
    });
    if (resetBtn) {
      resetBtn.addEventListener('click', function () { reset(form, resultEl); });
    }
  }

  function boot() {
    document.querySelectorAll('.q-quiz-form').forEach(init);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
