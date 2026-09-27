function viewSystem(systemId) {
    fetch(`/system/${systemId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displaySystemDetail(data.system);
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('システム情報の取得に失敗しました');
        });
}

function displaySystemDetail(system) {
    const modalBody = document.getElementById('modal-body');
    const html = `
        <table class="data-table">
            <tr><th>システムID</th><td>${system.system_id}</td></tr>
            <tr><th>システム名</th><td>${system.system_name}</td></tr>
            <tr><th>説明</th><td>${system.description || '-'}</td></tr>
            <tr><th>取り込み方法</th><td>${system.import_method || '-'}</td></tr>
            <tr><th>最終取り込み日時</th><td>${system.last_import_datetime || '-'}</td></tr>
            <tr><th>最終取り込みレコード数</th><td>${system.last_import_record_count || '-'}</td></tr>
            <tr><th>出力要否</th><td>${system.output_required ? '必要' : '不要'}</td></tr>
            <tr><th>出力順</th><td>${system.output_order || '-'}</td></tr>
            <tr><th>出力シート名</th><td>${system.output_sheet_name || '-'}</td></tr>
            <tr><th>退職者リスト表示SQL</th><td>${system.taishoku_display_sql || '-'}</td></tr>
            <tr><th>無効化済み判定式</th><td>${system.taishoku_disabled_expression || '-'}</td></tr>
            <tr><th>確認頻度</th><td>${system.check_frequency === 'MONTHLY' ? '月次' : system.check_frequency === 'ANNUAL' ? '年次（5月）' : system.check_frequency === 'NONE' ? '不要' : '-'}</td></tr>
            <tr><th>確認担当</th><td>${system.check_responsible || '-'}</td></tr>
            <tr><th>出力範囲</th><td>${system.output_scope || '-'}</td></tr>
            <tr><th>確認ポイント</th><td>${system.check_points || '-'}</td></tr>
            <tr><th>確認備考</th><td>${system.check_remarks || '-'}</td></tr>
            <tr><th>状態</th><td>${system.is_active ? '有効' : '無効'}</td></tr>
        </table>
    `;
    modalBody.innerHTML = html;

    document.getElementById('modal-title').textContent = 'システム詳細';
    document.getElementById('system-modal').style.display = 'block';
}

function editSystem(systemId) {
    fetch(`/system/${systemId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                populateEditForm(data.system);
                document.getElementById('edit-modal').style.display = 'block';
            } else {
                alert('エラー: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('システム情報の取得に失敗しました');
        });
}

function populateEditForm(system) {
    // モーダルタイトル変更
    const modalTitle = document.querySelector('#edit-modal h3');
    modalTitle.textContent = 'システム編集';

    // システムIDフィールドを非表示（編集時はシステムID変更不可）
    document.getElementById('system-id-field').style.display = 'none';
    document.getElementById('edit-system-id-input').required = false;

    document.getElementById('edit-system-id').value = system.system_id;
    document.getElementById('edit-system-name').value = system.system_name || '';
    document.getElementById('edit-description').value = system.description || '';
    document.getElementById('edit-output-order').value = system.output_order || '';
    document.getElementById('edit-output-sheet-name').value = system.output_sheet_name || '';

    document.getElementById('edit-import-method').value = system.import_method || '';
    document.getElementById('edit-import-mapping-json').value = system.import_mapping_json || '';
    document.getElementById('edit-import-table-name').value = system.import_table_name || '';

    const importTableNameRequired = document.getElementById('import-table-name-required');
    const helpDirect = document.getElementById('help-direct');
    const helpFile = document.getElementById('help-file');
    const sheetNameGroup = document.getElementById('sheet-name-group');

    if (system.import_method === 'DIRECT') {
        document.getElementById('direct-import-section').style.display = 'block';
        importTableNameRequired.style.display = 'inline';
        helpDirect.style.display = 'inline';
        helpFile.style.display = 'none';
        document.getElementById('mapping-section').style.display = 'none';
        if (sheetNameGroup) sheetNameGroup.style.display = 'none';
    } else if (system.import_method === 'CSV' || system.import_method === 'XLSX') {
        document.getElementById('direct-import-section').style.display = 'block';
        importTableNameRequired.style.display = 'none';
        helpDirect.style.display = 'none';
        helpFile.style.display = 'inline';
        document.getElementById('mapping-section').style.display = 'block';
        // シート名フィールドはXLSXの場合のみ表示
        if (sheetNameGroup) {
            sheetNameGroup.style.display = system.import_method === 'XLSX' ? 'block' : 'none';
        }
    } else {
        document.getElementById('direct-import-section').style.display = 'none';
        document.getElementById('mapping-section').style.display = 'none';
        if (sheetNameGroup) sheetNameGroup.style.display = 'none';
    }

    document.getElementById('edit-output-required').checked = system.output_required === 1;
    document.getElementById('edit-tanaoroshi-mode').value = system.tanaoroshi_output_mode || 'MISMATCH_ONLY';
    document.getElementById('edit-tanaoroshi-output-columns-json').value = system.tanaoroshi_output_columns_json || '';
    document.getElementById('edit-tanaoroshi-filter-sql').value = system.tanaoroshi_filter_sql || '';
    document.getElementById('edit-tanaoroshi-sort-sql').value = system.tanaoroshi_sort_sql || '';
    document.getElementById('edit-tenshutu-output-columns-json').value = system.tenshutu_output_columns_json || '';
    document.getElementById('edit-tenshutu-filter-sql').value = system.tenshutu_filter_sql || '';
    document.getElementById('edit-tenshutu-sort-sql').value = system.tenshutu_sort_sql || '';

    document.getElementById('edit-taishoku-required').checked = system.taishoku_output_required === 1;
    document.getElementById('edit-taishoku-order').value = system.taishoku_output_order || '';
    document.getElementById('edit-taishoku-display-sql').value = system.taishoku_display_sql || '';
    document.getElementById('edit-taishoku-disabled-expression').value = system.taishoku_disabled_expression || '';

    document.getElementById('edit-check-frequency').value = system.check_frequency || 'MONTHLY';
    document.getElementById('edit-check-responsible').value = system.check_responsible || '';
    document.getElementById('edit-output-scope').value = system.output_scope || '';
    document.getElementById('edit-check-points').value = system.check_points || '';
    document.getElementById('edit-check-remarks').value = system.check_remarks || '';

    document.getElementById('edit-is-active').checked = system.is_active === 1;
    document.getElementById('edit-remarks').value = system.remarks || '';

    // JSONからフォームビルダーに反映（マッピング定義）
    if (typeof jsonToMappingForm === 'function') {
        jsonToMappingForm();
    }

    // 利用可能なカラムを読み込んでから、出力項目定義を反映
    loadAvailableColumns(system.system_id).then(() => {
        if (typeof jsonToTanaoroshiOutputForm === 'function') {
            jsonToTanaoroshiOutputForm();
        }
        if (typeof jsonToTenshutuOutputForm === 'function') {
            jsonToTenshutuOutputForm();
        }
    });
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    document.getElementById('edit-system-form').reset();
    hideMessage('edit-result');
}

function openCreateModal() {
    document.getElementById('edit-system-form').reset();
    document.getElementById('edit-system-id').value = '';

    // モーダルタイトル変更
    const modalTitle = document.querySelector('#edit-modal h3');
    modalTitle.textContent = 'システム新規登録';

    // システムIDフィールドを表示
    document.getElementById('system-id-field').style.display = 'block';
    document.getElementById('edit-system-id-input').required = true;

    // デフォルト値設定
    document.getElementById('edit-output-required').checked = true;
    document.getElementById('edit-taishoku-required').checked = true;
    document.getElementById('edit-is-active').checked = true;
    document.getElementById('edit-tanaoroshi-mode').value = 'MISMATCH_ONLY';
    document.getElementById('edit-check-frequency').value = 'MONTHLY';

    // 初期状態でセクションを非表示
    document.getElementById('direct-import-section').style.display = 'none';
    document.getElementById('mapping-section').style.display = 'none';

    document.getElementById('edit-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('system-modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('system-modal');
    const editModal = document.getElementById('edit-modal');

    // 詳細表示モーダルのみ外側クリックで閉じる
    if (event.target === modal) {
        modal.style.display = 'none';
    }

    // 編集モーダルは外側クリックで閉じない（データ喪失防止）
    // event.target === editModal の場合は何もしない
}

document.addEventListener('DOMContentLoaded', function() {
    const editForm = document.getElementById('edit-system-form');
    if (editForm) {
        editForm.addEventListener('submit', handleEditSubmit);
    }
});

function handleEditSubmit(e) {
    e.preventDefault();

    // フォームビルダーからJSONに同期（バリデーション前に実行）
    if (document.getElementById('mapping-builder') && document.getElementById('mapping-builder').classList.contains('active')) {
        mappingFormToJson();
    }
    if (document.getElementById('tanaoroshi-output-builder') && document.getElementById('tanaoroshi-output-builder').classList.contains('active')) {
        syncTanaoroshiOutputJson();
    }
    if (document.getElementById('tenshutu-output-builder') && document.getElementById('tenshutu-output-builder').classList.contains('active')) {
        syncTenshutuOutputJson();
    }

    const importMethod = document.getElementById('edit-import-method').value;
    const mappingJsonField = document.getElementById('edit-import-mapping-json');
    const importTableNameField = document.getElementById('edit-import-table-name');

    const systemId = document.getElementById('edit-system-id').value;
    const isCreate = !systemId;

    // カスタムバリデーション
    if (importMethod === 'DIRECT' && !importTableNameField.value.trim()) {
        showMessage('edit-result', 'DIRECT参照の場合、参照元テーブル/SQLは必須です', 'error');
        return;
    }
    if ((importMethod === 'CSV' || importMethod === 'XLSX') && !mappingJsonField.value.trim()) {
        showMessage('edit-result', 'CSV/XLSX取り込みの場合、マッピング定義は必須です', 'error');
        return;
    }

    const formData = {
        system_id: systemId || document.getElementById('edit-system-id-input').value,
        system_name: document.getElementById('edit-system-name').value,
        description: document.getElementById('edit-description').value,
        import_method: document.getElementById('edit-import-method').value,
        import_table_name: document.getElementById('edit-import-table-name').value,
        import_mapping_json: document.getElementById('edit-import-mapping-json').value,
        output_required: document.getElementById('edit-output-required').checked ? 1 : 0,
        output_order: parseInt(document.getElementById('edit-output-order').value) || null,
        output_sheet_name: document.getElementById('edit-output-sheet-name').value,
        tanaoroshi_output_columns_json: document.getElementById('edit-tanaoroshi-output-columns-json').value,
        tanaoroshi_output_mode: document.getElementById('edit-tanaoroshi-mode').value,
        tanaoroshi_filter_sql: document.getElementById('edit-tanaoroshi-filter-sql').value,
        tanaoroshi_sort_sql: document.getElementById('edit-tanaoroshi-sort-sql').value,
        tenshutu_output_columns_json: document.getElementById('edit-tenshutu-output-columns-json').value,
        tenshutu_filter_sql: document.getElementById('edit-tenshutu-filter-sql').value,
        tenshutu_sort_sql: document.getElementById('edit-tenshutu-sort-sql').value,
        taishoku_output_required: document.getElementById('edit-taishoku-required').checked ? 1 : 0,
        taishoku_output_order: parseInt(document.getElementById('edit-taishoku-order').value) || null,
        taishoku_display_sql: document.getElementById('edit-taishoku-display-sql').value,
        taishoku_disabled_expression: document.getElementById('edit-taishoku-disabled-expression').value,
        check_frequency: document.getElementById('edit-check-frequency').value,
        check_responsible: document.getElementById('edit-check-responsible').value,
        output_scope: document.getElementById('edit-output-scope').value,
        check_points: document.getElementById('edit-check-points').value,
        check_remarks: document.getElementById('edit-check-remarks').value,
        is_active: document.getElementById('edit-is-active').checked ? 1 : 0,
        remarks: document.getElementById('edit-remarks').value,
        user: 'system'
    };

    // JSON検証
    if (formData.import_mapping_json) {
        try {
            JSON.parse(formData.import_mapping_json);
        } catch (e) {
            showMessage('edit-result', 'マッピング定義のJSONが不正です: ' + e.message, 'error');
            return;
        }
    }

    if (formData.tanaoroshi_output_columns_json) {
        try {
            JSON.parse(formData.tanaoroshi_output_columns_json);
        } catch (e) {
            showMessage('edit-result', '棚卸リスト出力項目定義のJSONが不正です: ' + e.message, 'error');
            return;
        }
    }

    if (formData.tenshutu_output_columns_json) {
        try {
            JSON.parse(formData.tenshutu_output_columns_json);
        } catch (e) {
            showMessage('edit-result', '転出者リスト出力項目定義のJSONが不正です: ' + e.message, 'error');
            return;
        }
    }

    showMessage('edit-result', '保存中...', '');

    const url = isCreate ? '/system/create' : `/system/update/${systemId}`;
    const method = isCreate ? 'POST' : 'PUT';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('edit-result', data.message, 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showMessage('edit-result', 'エラー: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('edit-result', '更新に失敗しました', 'error');
    });
}

document.getElementById('edit-import-method').addEventListener('change', function() {
    const method = this.value;
    const directSection = document.getElementById('direct-import-section');
    const mappingSection = document.getElementById('mapping-section');
    const mappingBuilder = document.getElementById('mapping-builder');
    const mappingJson = document.getElementById('mapping-json');
    const importTableNameRequired = document.getElementById('import-table-name-required');
    const helpDirect = document.getElementById('help-direct');
    const helpFile = document.getElementById('help-file');
    const sheetNameGroup = document.getElementById('sheet-name-group');

    if (method === 'DIRECT') {
        // DIRECT: IMPORT_TABLE_NAMEは必須、マッピング不要
        directSection.style.display = 'block';
        importTableNameRequired.style.display = 'inline';
        helpDirect.style.display = 'inline';
        helpFile.style.display = 'none';

        mappingSection.style.display = 'none';
        if (sheetNameGroup) sheetNameGroup.style.display = 'none';
    } else if (method === 'CSV' || method === 'XLSX') {
        // CSV/XLSX: IMPORT_TABLE_NAMEは任意（追加SQL処理用）、マッピングは必須
        directSection.style.display = 'block';
        importTableNameRequired.style.display = 'none';
        helpDirect.style.display = 'none';
        helpFile.style.display = 'inline';

        mappingSection.style.display = 'block';

        // シート名フィールドはXLSXの場合のみ表示
        if (sheetNameGroup) {
            sheetNameGroup.style.display = method === 'XLSX' ? 'block' : 'none';
        }

        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab && activeTab.textContent === 'フォーム入力') {
            mappingBuilder.style.display = 'block';
            mappingJson.style.display = 'none';
        } else {
            mappingBuilder.style.display = 'none';
            mappingJson.style.display = 'block';
        }
    } else {
        // その他
        directSection.style.display = 'none';
        mappingSection.style.display = 'none';
        if (sheetNameGroup) sheetNameGroup.style.display = 'none';
    }
});

// 棚卸リスト出力カラム管理
let tanaoroshiAvailableColumns = {
    system: [],
    zaiseki: []
};

function addTanaoroshiOutputColumn() {
    const tbody = document.getElementById('tanaoroshi-output-columns-body');
    const row = tbody.insertRow();
    const index = tbody.rows.length;

    row.innerHTML = `
        <td>
            <select class="tanaoroshi-source-select" onchange="updateTanaoroshiColumnOptions(this)" data-index="${index}">
                <option value="">選択してください</option>
                <option value="system">システム</option>
                <option value="zaiseki">在籍</option>
            </select>
        </td>
        <td>
            <select class="tanaoroshi-column-select" data-index="${index}" disabled>
                <option value="">まずソースを選択</option>
            </select>
        </td>
        <td><input type="text" class="tanaoroshi-display-name" placeholder="表示名"></td>
        <td><input type="number" class="tanaoroshi-order" value="${index}" min="1"></td>
        <td><button type="button" class="btn btn-small btn-danger" onclick="removeTanaoroshiOutputColumn(this)">削除</button></td>
    `;

    syncTanaoroshiOutputJson();
}

function removeTanaoroshiOutputColumn(btn) {
    btn.closest('tr').remove();
    syncTanaoroshiOutputJson();
}

function updateTanaoroshiColumnOptions(selectElement) {
    const source = selectElement.value;
    const index = selectElement.dataset.index;
    const columnSelect = document.querySelector(`.tanaoroshi-column-select[data-index="${index}"]`);

    if (!source) {
        columnSelect.disabled = true;
        columnSelect.innerHTML = '<option value="">まずソースを選択</option>';
        return;
    }

    columnSelect.disabled = false;
    columnSelect.innerHTML = '<option value="">選択してください</option>';

    const columns = tanaoroshiAvailableColumns[source] || [];
    columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col.value;
        option.textContent = col.label;
        columnSelect.appendChild(option);
    });

    syncTanaoroshiOutputJson();
}

function syncTanaoroshiOutputJson() {
    const tbody = document.getElementById('tanaoroshi-output-columns-body');
    const columns = [];

    Array.from(tbody.rows).forEach(row => {
        const sourceSelect = row.querySelector('.tanaoroshi-source-select');
        const columnSelect = row.querySelector('.tanaoroshi-column-select');
        const displayName = row.querySelector('.tanaoroshi-display-name').value;
        const order = row.querySelector('.tanaoroshi-order').value;

        if (sourceSelect.value && columnSelect.value) {
            columns.push({
                source: sourceSelect.value,
                column_name: columnSelect.value,
                display_name: displayName || columnSelect.options[columnSelect.selectedIndex].text,
                order: parseInt(order) || 1
            });
        }
    });

    document.getElementById('edit-tanaoroshi-output-columns-json').value = JSON.stringify({ columns }, null, 2);
}

// 転出者リスト出力カラム管理
let tenshutuAvailableColumns = {
    system: [],
    tenshutu: []
};

function addTenshutuOutputColumn() {
    const tbody = document.getElementById('tenshutu-output-columns-body');
    const row = tbody.insertRow();
    const index = tbody.rows.length;

    row.innerHTML = `
        <td>
            <select class="tenshutu-source-select" onchange="updateTenshutuColumnOptions(this)" data-index="${index}">
                <option value="">選択してください</option>
                <option value="system">システム</option>
                <option value="tenshutu">異動</option>
            </select>
        </td>
        <td>
            <select class="tenshutu-column-select" data-index="${index}" disabled>
                <option value="">まずソースを選択</option>
            </select>
        </td>
        <td><input type="text" class="tenshutu-display-name" placeholder="表示名"></td>
        <td><input type="number" class="tenshutu-order" value="${index}" min="1"></td>
        <td><button type="button" class="btn btn-small btn-danger" onclick="removeTenshutuOutputColumn(this)">削除</button></td>
    `;

    syncTenshutuOutputJson();
}

function removeTenshutuOutputColumn(btn) {
    btn.closest('tr').remove();
    syncTenshutuOutputJson();
}

function updateTenshutuColumnOptions(selectElement) {
    const source = selectElement.value;
    const index = selectElement.dataset.index;
    const columnSelect = document.querySelector(`.tenshutu-column-select[data-index="${index}"]`);

    if (!source) {
        columnSelect.disabled = true;
        columnSelect.innerHTML = '<option value="">まずソースを選択</option>';
        return;
    }

    columnSelect.disabled = false;
    columnSelect.innerHTML = '<option value="">選択してください</option>';

    const columns = tenshutuAvailableColumns[source] || [];
    columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col.value;
        option.textContent = col.label;
        columnSelect.appendChild(option);
    });

    syncTenshutuOutputJson();
}

function syncTenshutuOutputJson() {
    const tbody = document.getElementById('tenshutu-output-columns-body');
    const columns = [];

    Array.from(tbody.rows).forEach(row => {
        const sourceSelect = row.querySelector('.tenshutu-source-select');
        const columnSelect = row.querySelector('.tenshutu-column-select');
        const displayName = row.querySelector('.tenshutu-display-name').value;
        const order = row.querySelector('.tenshutu-order').value;

        if (sourceSelect.value && columnSelect.value) {
            columns.push({
                source: sourceSelect.value,
                column_name: columnSelect.value,
                display_name: displayName || columnSelect.options[columnSelect.selectedIndex].text,
                order: parseInt(order) || 1
            });
        }
    });

    document.getElementById('edit-tenshutu-output-columns-json').value = JSON.stringify({ columns }, null, 2);
}

// 利用可能なカラムを取得
function loadAvailableColumns(systemId) {
    if (!systemId) return Promise.resolve();

    return fetch(`/system/${systemId}/available-columns`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                tanaoroshiAvailableColumns.system = data.system_columns;
                tanaoroshiAvailableColumns.zaiseki = data.zaiseki_columns;
                tenshutuAvailableColumns.system = data.system_columns;
                tenshutuAvailableColumns.tenshutu = data.ido_columns;
            }
        })
        .catch(error => {
            console.error('Error loading available columns:', error);
        });
}

// JSONから棚卸リスト出力フォームビルダーに反映
function jsonToTanaoroshiOutputForm() {
    try {
        const jsonText = document.getElementById('edit-tanaoroshi-output-columns-json').value;
        if (!jsonText || jsonText.trim() === '') return;

        const data = JSON.parse(jsonText);
        const tbody = document.getElementById('tanaoroshi-output-columns-body');
        tbody.innerHTML = '';

        if (data.columns && Array.isArray(data.columns)) {
            data.columns.forEach((col, index) => {
                const row = tbody.insertRow();
                const rowIndex = tbody.rows.length;

                row.innerHTML = `
                    <td>
                        <select class="tanaoroshi-source-select" onchange="updateTanaoroshiColumnOptions(this)" data-index="${rowIndex}">
                            <option value="">選択してください</option>
                            <option value="system" ${col.source === 'system' ? 'selected' : ''}>システム</option>
                            <option value="zaiseki" ${col.source === 'zaiseki' ? 'selected' : ''}>在籍</option>
                        </select>
                    </td>
                    <td>
                        <select class="tanaoroshi-column-select" data-index="${rowIndex}">
                            <option value="${col.column_name}">${col.column_name}</option>
                        </select>
                    </td>
                    <td><input type="text" class="tanaoroshi-display-name" value="${col.display_name || ''}" placeholder="表示名"></td>
                    <td><input type="number" class="tanaoroshi-order" value="${col.order || rowIndex}" min="1"></td>
                    <td><button type="button" class="btn btn-small btn-danger" onclick="removeTanaoroshiOutputColumn(this)">削除</button></td>
                `;

                // カラムオプションを更新
                const sourceSelect = row.querySelector('.tanaoroshi-source-select');
                updateTanaoroshiColumnOptions(sourceSelect);

                // 選択されたカラムを設定
                setTimeout(() => {
                    const columnSelect = row.querySelector('.tanaoroshi-column-select');
                    columnSelect.value = col.column_name;
                }, 100);
            });
        }
    } catch (e) {
        console.error('Failed to parse tanaoroshi output columns JSON:', e);
    }
}

// JSONから転出者リスト出力フォームビルダーに反映
function jsonToTenshutuOutputForm() {
    try {
        const jsonText = document.getElementById('edit-tenshutu-output-columns-json').value;
        if (!jsonText || jsonText.trim() === '') return;

        const data = JSON.parse(jsonText);
        const tbody = document.getElementById('tenshutu-output-columns-body');
        tbody.innerHTML = '';

        if (data.columns && Array.isArray(data.columns)) {
            data.columns.forEach((col, index) => {
                const row = tbody.insertRow();
                const rowIndex = tbody.rows.length;

                row.innerHTML = `
                    <td>
                        <select class="tenshutu-source-select" onchange="updateTenshutuColumnOptions(this)" data-index="${rowIndex}">
                            <option value="">選択してください</option>
                            <option value="system" ${col.source === 'system' ? 'selected' : ''}>システム</option>
                            <option value="tenshutu" ${col.source === 'tenshutu' ? 'selected' : ''}>異動</option>
                        </select>
                    </td>
                    <td>
                        <select class="tenshutu-column-select" data-index="${rowIndex}">
                            <option value="${col.column_name}">${col.column_name}</option>
                        </select>
                    </td>
                    <td><input type="text" class="tenshutu-display-name" value="${col.display_name || ''}" placeholder="表示名"></td>
                    <td><input type="number" class="tenshutu-order" value="${col.order || rowIndex}" min="1"></td>
                    <td><button type="button" class="btn btn-small btn-danger" onclick="removeTenshutuOutputColumn(this)">削除</button></td>
                `;

                // カラムオプションを更新
                const sourceSelect = row.querySelector('.tenshutu-source-select');
                updateTenshutuColumnOptions(sourceSelect);

                // 選択されたカラムを設定
                setTimeout(() => {
                    const columnSelect = row.querySelector('.tenshutu-column-select');
                    columnSelect.value = col.column_name;
                }, 100);
            });
        }
    } catch (e) {
        console.error('Failed to parse tenshutu output columns JSON:', e);
    }
}
