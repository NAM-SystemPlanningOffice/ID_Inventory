document.getElementById('org-change-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = {
        change_date: document.getElementById('change-date').value,
        before_org_cd: document.getElementById('before-org-cd').value,
        before_org_name: document.getElementById('before-org-name').value,
        after_org_cd: document.getElementById('after-org-cd').value,
        after_org_name: document.getElementById('after-org-name').value,
        remarks: document.getElementById('remarks').value
    };

    fetch('/organization/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('org-result', data.message, 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showMessage('org-result', 'エラー: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('org-result', '登録に失敗しました', 'error');
    });
});

function deleteChange(changeDate, beforeOrgCd, afterOrgCd) {
    if (!confirm('この組織変更を削除しますか?')) {
        return;
    }

    fetch('/organization/delete', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            change_date: changeDate,
            before_org_cd: beforeOrgCd,
            after_org_cd: afterOrgCd
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            location.reload();
        } else {
            alert('エラー: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('削除に失敗しました');
    });
}
