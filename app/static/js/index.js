function loadIdoTaishokuDates() {
    const monthInput = document.getElementById('target-month');
    const yearMonth = monthInput.value;

    if (!yearMonth) {
        alert('対象月を選択してください');
        return;
    }

    fetch(`/api/ido-taishoku-dates/${yearMonth}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayDateList(data.dates);
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('日付の取得に失敗しました');
        });
}

function displayDateList(dates) {
    const dateListDiv = document.getElementById('date-list');

    if (dates.length === 0) {
        dateListDiv.innerHTML = '<p class="warning">該当する日付がありません</p>';
        return;
    }

    let html = '<ul>';
    dates.forEach(dateInfo => {
        const tags = [];
        if (dateInfo.has_taishoku) tags.push('退職');
        if (dateInfo.has_ido) tags.push('転出');

        html += `<li>
            <strong>${formatDate(dateInfo.date)}</strong>
            <span class="tag">${tags.join(', ')}</span>
            <a href="/output?date=${dateInfo.date}" class="btn btn-small">リスト出力</a>
        </li>`;
    });
    html += '</ul>';

    dateListDiv.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const currentMonth = today.toISOString().slice(0, 7);
    document.getElementById('target-month').value = currentMonth;
});
