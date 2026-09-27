// ページ読み込み時に退職・異動日リストを取得
document.addEventListener('DOMContentLoaded', function() {
    loadTaishokuIdoDates();
});

function loadTaishokuIdoDates() {
    const loadingDiv = document.getElementById('date-list-loading');
    const errorDiv = document.getElementById('date-list-error');
    const formDiv = document.getElementById('taishoku-tenshutu-form');
    const selectElement = document.getElementById('target-date');

    fetch('/output/dates')
        .then(response => response.json())
        .then(data => {
            loadingDiv.style.display = 'none';

            if (data.status === 'success' && data.dates && data.dates.length > 0) {
                data.dates.forEach(dateInfo => {
                    const option = document.createElement('option');
                    // 日付部分のみを抽出してvalueに設定
                    option.value = extractDateOnly(dateInfo.IDO_DATE);
                    const dateStr = formatDate(dateInfo.IDO_DATE);
                    const taishokuCount = dateInfo.TAISHA_COUNT || 0;
                    const idoCount = dateInfo.IDO_COUNT || 0;
                    option.textContent = `${dateStr} (退職・産育休: ${taishokuCount}件、異動: ${idoCount}件)`;
                    selectElement.appendChild(option);
                });
                formDiv.style.display = 'block';
            } else {
                errorDiv.textContent = '過去200日間に退職・異動の記録がありません';
                errorDiv.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingDiv.style.display = 'none';
            errorDiv.textContent = '日付リストの取得に失敗しました';
            errorDiv.style.display = 'block';
        });
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}年${month}月${day}日`;
}

function extractDateOnly(dateStr) {
    if (!dateStr) return '';
    // ISO形式の日付文字列から日付部分のみを抽出 (YYYY-MM-DD)
    if (dateStr.indexOf('T') > 0) {
        return dateStr.split('T')[0];
    }
    return dateStr.substring(0, 10);
}

// 棚卸リスト生成フォーム
document.getElementById('tanaoroshi-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const resultDiv = document.getElementById('tanaoroshi-result');

    resultDiv.textContent = '生成中...';
    resultDiv.className = 'result-message';
    resultDiv.style.display = 'block';

    fetch('/output/tanaoroshi', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success' || data.status === 'warning') {
            let html = `${data.message}<br><a href="${data.url}" target="_blank" class="btn btn-small">スプレッドシートを開く</a>`;

            // SQLエラーが発生したシステムがあれば内容を表示（修正の手掛かり）
            if (data.error_systems && data.error_systems.length > 0) {
                html += '<div class="sql-error-list" style="margin-top: 12px; padding: 10px; border: 1px solid #e0b400; background: #fff8e1; border-radius: 4px;">';
                html += '<strong>⚠ 以下のシステムでSQLエラーが発生し、シート出力されていません。「システム定義」の設定を修正してください。</strong>';
                html += '<ul style="margin: 8px 0 0 0; padding-left: 20px;">';
                data.error_systems.forEach(function(es) {
                    html += '<li style="margin-bottom: 6px;"><strong>' + escapeHtml(es.system_name) +
                            '</strong> (' + escapeHtml(es.system_id) + ')<br>' +
                            '<code style="word-break: break-all; white-space: pre-wrap;">' + escapeHtml(es.error) + '</code></li>';
                });
                html += '</ul></div>';
            }

            resultDiv.innerHTML = html;
            resultDiv.className = 'result-message ' + (data.status === 'warning' ? 'warning' : 'success');
        } else {
            resultDiv.textContent = 'エラー: ' + data.message;
            resultDiv.className = 'result-message error';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        resultDiv.textContent = '生成に失敗しました';
        resultDiv.className = 'result-message error';
    });
});

// HTMLエスケープ（SQLエラー文言などを安全に表示）
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// 退職者・転出者リスト生成フォーム
document.getElementById('taishoku-tenshutu-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const targetDate = document.getElementById('target-date').value;
    const resultDiv = document.getElementById('taishoku-tenshutu-result');

    if (!targetDate) {
        resultDiv.textContent = '対象日を選択してください';
        resultDiv.className = 'result-message error';
        resultDiv.style.display = 'block';
        return;
    }

    resultDiv.textContent = '生成中...';
    resultDiv.className = 'result-message';
    resultDiv.style.display = 'block';

    fetch('/output/taishoku-tenshutu', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ target_date: targetDate })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success' || data.status === 'warning') {
            let html = data.message;

            // SQLエラーが発生した場合は内容を表示（修正の手掛かり）
            if (data.errors && data.errors.length > 0) {
                html += '<div class="sql-error-list" style="margin-top: 12px; padding: 10px; border: 1px solid #e0b400; background: #fff8e1; border-radius: 4px;">';
                html += '<strong>⚠ 以下のリスト生成でSQLエラーが発生しました。「システム定義」の設定を修正してください。</strong>';
                html += '<ul style="margin: 8px 0 0 0; padding-left: 20px;">';
                data.errors.forEach(function(err) {
                    html += '<li style="margin-bottom: 6px;"><code style="word-break: break-all; white-space: pre-wrap;">' + escapeHtml(err) + '</code></li>';
                });
                html += '</ul></div>';
            }

            // URLが存在する場合のみリンクを表示
            if (data.taishoku_url || data.tenshutu_url) {
                html += '<br><div style="display: flex; gap: 10px; margin-top: 10px;">';
                if (data.taishoku_url) {
                    html += '<a href="' + data.taishoku_url + '" target="_blank" class="btn btn-small">退職者リストを開く</a>';
                }
                if (data.tenshutu_url) {
                    html += '<a href="' + data.tenshutu_url + '" target="_blank" class="btn btn-small">転出者リストを開く</a>';
                }
                html += '</div>';
            }

            resultDiv.innerHTML = html;
            resultDiv.className = 'result-message ' + (data.status === 'warning' ? 'warning' : 'success');
        } else {
            resultDiv.textContent = 'エラー: ' + data.message;
            resultDiv.className = 'result-message error';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        resultDiv.textContent = '生成に失敗しました';
        resultDiv.className = 'result-message error';
    });
});
