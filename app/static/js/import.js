document.getElementById('upload-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const resultDiv = document.getElementById('upload-result');

    resultDiv.textContent = 'アップロード中...';
    resultDiv.className = 'result-message';
    resultDiv.style.display = 'block';

    fetch('/import/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            let message = `取り込み成功: ${data.system_name} - ${data.records}件`;
            let messageType = 'success';
            let hasWarnings = false;

            // 警告がある場合
            if (data.warnings && data.warnings.skipped_rows > 0) {
                hasWarnings = true;
                messageType = 'warning';
                message = `取り込み完了（警告あり）: ${data.system_name} - ${data.records}件取り込み、${data.warnings.skipped_rows}件スキップ\n\n`;
                message += '【スキップされた行（最大10件表示）】\n';
                data.warnings.errors.forEach(err => {
                    message += `行${err.row}: ${err.message}\n`;
                });
                message += '\n\n※ 内容を確認したら、画面を更新してください';
            }

            showMessage('upload-result', message, messageType);

            // 警告がない場合のみ自動リロード
            if (!hasWarnings) {
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }
        } else {
            showMessage('upload-result', 'エラー: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('upload-result', '取り込みに失敗しました', 'error');
    });
});

document.getElementById('system-select').addEventListener('change', function() {
    const systemId = this.value;
    if (!systemId) return;

    fetch(`/import/system/${systemId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('System info:', data.system);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
});
