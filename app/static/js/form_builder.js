// タブ切り替え
function switchTab(type, tab) {
    const builderTab = document.querySelector(`button[onclick="switchTab('${type}', 'builder')"]`);
    const jsonTab = document.querySelector(`button[onclick="switchTab('${type}', 'json')"]`);
    const builderContent = document.getElementById(`${type}-builder`);
    const jsonContent = document.getElementById(`${type}-json`);

    if (tab === 'builder') {
        builderTab.classList.add('active');
        jsonTab.classList.remove('active');
        builderContent.classList.add('active');
        jsonContent.classList.remove('active');

        // JSON → フォームに同期
        if (type === 'mapping') {
            jsonToMappingForm();
        } else if (type === 'output') {
            jsonToOutputForm();
        } else if (type === 'tanaoroshi-output' && typeof jsonToTanaoroshiOutputForm === 'function') {
            jsonToTanaoroshiOutputForm();
        } else if (type === 'tenshutu-output' && typeof jsonToTenshutuOutputForm === 'function') {
            jsonToTenshutuOutputForm();
        }
    } else {
        builderTab.classList.remove('active');
        jsonTab.classList.add('active');
        builderContent.classList.remove('active');
        jsonContent.classList.add('active');

        // フォーム → JSONに同期
        if (type === 'mapping') {
            mappingFormToJson();
        } else if (type === 'output') {
            outputFormToJson();
        } else if (type === 'tanaoroshi-output' && typeof syncTanaoroshiOutputJson === 'function') {
            syncTanaoroshiOutputJson();
        } else if (type === 'tenshutu-output' && typeof syncTenshutuOutputJson === 'function') {
            syncTenshutuOutputJson();
        }
    }
}

// マッピング定義：列追加
function addMappingColumn(data = {}) {
    const tbody = document.getElementById('mapping-columns-body');
    const row = tbody.insertRow();
    const hasHeader = document.getElementById('mapping-has-header').checked;

    row.innerHTML = `
        <td><input type="text" class="map-source-col" value="${data.source_column || ''}" placeholder="${hasHeader ? '例: ユーザーID' : '（任意）'}" style="${hasHeader ? '' : 'background-color: #f5f5f5;'}"></td>
        <td><input type="number" class="map-source-idx" value="${data.source_index !== undefined ? data.source_index : ''}" min="0" placeholder="${hasHeader ? '（任意）' : '例: 0'}" style="${hasHeader ? 'background-color: #f5f5f5;' : ''}"></td>
        <td><input type="text" class="map-target-col" value="${data.target_column || ''}" placeholder="例: USER_CD" required></td>
        <td>
            <select class="map-data-type">
                <option value="string" ${data.data_type === 'string' || !data.data_type ? 'selected' : ''}>string</option>
                <option value="number" ${data.data_type === 'number' ? 'selected' : ''}>number</option>
                <option value="date" ${data.data_type === 'date' ? 'selected' : ''}>date</option>
            </select>
        </td>
        <td><input type="checkbox" class="map-required" ${data.required ? 'checked' : ''}></td>
        <td><input type="checkbox" class="map-trim" ${data.trim ? 'checked' : ''}></td>
        <td>
            <select class="map-transform">
                <option value="" ${!data.transform ? 'selected' : ''}>なし</option>
                <option value="lowercase" ${data.transform === 'lowercase' ? 'selected' : ''}>小文字</option>
                <option value="uppercase" ${data.transform === 'uppercase' ? 'selected' : ''}>大文字</option>
            </select>
        </td>
        <td><button type="button" class="btn btn-small btn-danger" onclick="this.closest('tr').remove()">削除</button></td>
    `;
}

// 出力項目定義：列追加
function addOutputColumn(data = {}) {
    const tbody = document.getElementById('output-columns-body');
    const row = tbody.insertRow();
    row.innerHTML = `
        <td><input type="text" class="out-col-name" value="${data.column_name || ''}" placeholder="例: USER_CD"></td>
        <td><input type="text" class="out-display-name" value="${data.display_name || ''}" placeholder="例: ユーザーID"></td>
        <td><input type="number" class="out-order" value="${data.order || ''}" min="1"></td>
        <td><input type="number" class="out-width" value="${data.width || 15}" min="5"></td>
        <td>
            <select class="out-format">
                <option value="text" ${!data.format || data.format === 'text' ? 'selected' : ''}>text</option>
                <option value="number" ${data.format === 'number' ? 'selected' : ''}>number</option>
                <option value="date" ${data.format === 'date' ? 'selected' : ''}>date</option>
            </select>
        </td>
        <td><button type="button" class="btn btn-small btn-danger" onclick="this.closest('tr').remove()">削除</button></td>
    `;
}

// マッピング定義：フォーム → JSON
function mappingFormToJson() {
    const encoding = document.getElementById('mapping-encoding').value;
    const delimiterSelect = document.getElementById('mapping-delimiter').value;
    const delimiterCustom = document.getElementById('mapping-delimiter-custom').value;
    const quotechar = document.getElementById('mapping-quotechar').value;
    const hasHeader = document.getElementById('mapping-has-header').checked;
    const skipRows = parseInt(document.getElementById('mapping-skip-rows').value) || 0;
    const sheetName = document.getElementById('mapping-sheet-name')?.value || '';

    // 区切り文字の決定
    let delimiter;
    if (delimiterSelect === 'custom') {
        delimiter = delimiterCustom || ',';
    } else if (delimiterSelect === '\\t') {
        delimiter = '\t';  // タブ文字に変換
    } else {
        delimiter = delimiterSelect;
    }

    const columns = [];
    const rows = document.querySelectorAll('#mapping-columns-body tr');

    rows.forEach(row => {
        const sourceCol = row.querySelector('.map-source-col').value;
        const sourceIdx = row.querySelector('.map-source-idx').value;
        const targetCol = row.querySelector('.map-target-col').value;
        const dataType = row.querySelector('.map-data-type').value;
        const required = row.querySelector('.map-required').checked;
        const trim = row.querySelector('.map-trim').checked;
        const transform = row.querySelector('.map-transform').value;

        if (targetCol) {
            const col = {
                target_column: targetCol,
                data_type: dataType,
                required: required,
                trim: trim
            };

            if (sourceCol) col.source_column = sourceCol;
            if (sourceIdx !== '') col.source_index = parseInt(sourceIdx);
            if (transform) col.transform = transform;

            columns.push(col);
        }
    });

    const mappingObj = {
        file_encoding: encoding,
        delimiter: delimiter,
        quotechar: quotechar,
        has_header: hasHeader,
        skip_rows: skipRows,
        columns: columns
    };

    // XLSXの場合のみシート名を追加
    if (sheetName) {
        mappingObj.sheet_name = sheetName;
    }

    document.getElementById('edit-import-mapping-json').value = JSON.stringify(mappingObj, null, 2);
}

// マッピング定義：JSON → フォーム
function jsonToMappingForm() {
    const json = document.getElementById('edit-import-mapping-json').value;
    if (!json) return;

    try {
        const mapping = JSON.parse(json);

        document.getElementById('mapping-encoding').value = mapping.file_encoding || 'utf-8';

        // 区切り文字の設定
        const delimiter = mapping.delimiter || ',';
        if (delimiter === '\t') {
            document.getElementById('mapping-delimiter').value = '\\t';
        } else if ([',', ';', '|'].includes(delimiter)) {
            document.getElementById('mapping-delimiter').value = delimiter;
        } else {
            document.getElementById('mapping-delimiter').value = 'custom';
            document.getElementById('mapping-delimiter-custom').value = delimiter;
            document.getElementById('delimiter-custom-group').style.display = 'block';
        }

        document.getElementById('mapping-quotechar').value = mapping.quotechar || '"';
        document.getElementById('mapping-has-header').checked = mapping.has_header !== false;
        document.getElementById('mapping-skip-rows').value = mapping.skip_rows || 0;

        // シート名の設定
        const sheetNameInput = document.getElementById('mapping-sheet-name');
        if (sheetNameInput) {
            sheetNameInput.value = mapping.sheet_name || '';
        }

        const tbody = document.getElementById('mapping-columns-body');
        tbody.innerHTML = '';

        if (mapping.columns) {
            mapping.columns.forEach(col => addMappingColumn(col));
        }
    } catch (e) {
        console.error('JSON parse error:', e);
    }
}

// 出力項目定義：フォーム → JSON
function outputFormToJson() {
    const columns = [];
    const rows = document.querySelectorAll('#output-columns-body tr');

    rows.forEach(row => {
        const colName = row.querySelector('.out-col-name').value;
        const displayName = row.querySelector('.out-display-name').value;
        const order = parseInt(row.querySelector('.out-order').value) || 1;
        const width = parseInt(row.querySelector('.out-width').value) || 15;
        const format = row.querySelector('.out-format').value;

        if (colName) {
            columns.push({
                column_name: colName,
                display_name: displayName,
                order: order,
                width: width,
                format: format
            });
        }
    });

    const outputObj = {
        columns: columns
    };

    document.getElementById('edit-output-columns-json').value = JSON.stringify(outputObj, null, 2);
}

// 出力項目定義：JSON → フォーム
function jsonToOutputForm() {
    const json = document.getElementById('edit-output-columns-json').value;
    if (!json) return;

    try {
        const output = JSON.parse(json);

        const tbody = document.getElementById('output-columns-body');
        tbody.innerHTML = '';

        if (output.columns) {
            output.columns.forEach(col => addOutputColumn(col));
        }
    } catch (e) {
        console.error('JSON parse error:', e);
    }
}

// ヘッダー行チェックボックスの変更を監視
function updateMappingColumnPlaceholders() {
    const hasHeader = document.getElementById('mapping-has-header').checked;
    const sourceColInputs = document.querySelectorAll('.map-source-col');
    const sourceIdxInputs = document.querySelectorAll('.map-source-idx');

    if (hasHeader) {
        sourceColInputs.forEach(input => {
            input.placeholder = '例: ユーザーID';
            input.style.backgroundColor = '';
        });
        sourceIdxInputs.forEach(input => {
            input.placeholder = '（任意）';
            input.style.backgroundColor = '#f5f5f5';
        });
    } else {
        sourceColInputs.forEach(input => {
            input.placeholder = '（任意）';
            input.style.backgroundColor = '#f5f5f5';
        });
        sourceIdxInputs.forEach(input => {
            input.placeholder = '例: 0';
            input.style.backgroundColor = '';
        });
    }
}

// 初期化
document.addEventListener('DOMContentLoaded', function() {
    // デフォルトで1行追加
    const mappingColumnsBody = document.getElementById('mapping-columns-body');
    if (mappingColumnsBody && mappingColumnsBody.children.length === 0) {
        addMappingColumn({
            source_column: 'ユーザーID',
            target_column: 'USER_CD',
            data_type: 'string',
            required: true,
            trim: true
        });
    }

    const outputColumnsBody = document.getElementById('output-columns-body');
    if (outputColumnsBody && outputColumnsBody.children.length === 0) {
        addOutputColumn({
            column_name: 'USER_CD',
            display_name: 'ユーザーID',
            order: 1,
            width: 15,
            format: 'text'
        });
    }

    // ヘッダー行チェックボックスのイベントリスナー
    const hasHeaderCheckbox = document.getElementById('mapping-has-header');
    if (hasHeaderCheckbox) {
        hasHeaderCheckbox.addEventListener('change', updateMappingColumnPlaceholders);
    }

    // 区切り文字選択のイベントリスナー
    const delimiterSelect = document.getElementById('mapping-delimiter');
    if (delimiterSelect) {
        delimiterSelect.addEventListener('change', function() {
            const customGroup = document.getElementById('delimiter-custom-group');
            if (this.value === 'custom') {
                customGroup.style.display = 'block';
            } else {
                customGroup.style.display = 'none';
            }
        });
    }
});
