        const API_BASE = "http://localhost:8000";
        let sceneCount = 0;
        let scenes = [];

        // Init Version
        (async function initVersion() {
            try {
                const res = await fetch(`${API_BASE}/api/version`);
                if (res.ok) {
                    const data = await res.json();
                    const header = document.getElementById('version-header');
                    if (header) {
                        header.innerText = `v${data.version.replace(/^v/, '')}`; // Ensure v prefix
                        header.title = `Build: ${data.build_time}`; // Tooltip for details
                    }
                }
            } catch (e) {
                console.error("Failed to fetch version", e);
                const header = document.getElementById('version-header');
                if (header) header.innerText = "Dev Mode";
            }
        })();

        function switchMode(mode) {
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`btn-${mode}`).classList.add('active');
            
            document.getElementById('studio-panel').classList.add('hidden');
            document.getElementById('storyboard-panel').classList.add('hidden');
            document.getElementById('character-panel').classList.add('hidden');
            
            document.getElementById(`${mode}-panel`).classList.remove('hidden');
            
            if (mode === 'storyboard' && sceneCount === 0) {
                 addScene(); // Auto add first scene
            }
            
            if (mode === 'character') {
                loadCharacters();
            }
        }

        // --- Character Logic ---
        async function loadCharacters() {
            try {
                const res = await fetch(`${API_BASE}/characters`);
                const chars = await res.json();
                
                const list = document.getElementById('my-char-list');
                list.innerHTML = '';
                if (chars.length === 0) {
                     list.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:20px;">暂无角色 (No characters yet)</div>';
                     return;
                }
                chars.forEach((c, index) => {
                    const name = c.name || c.username || 'Unknown';
                    
                    const clickAction = c.permalink ? `onclick="window.open('${c.permalink}', '_blank')"` : '';
                    const cursorStyle = c.permalink ? 'cursor: pointer;' : '';

                    // Use c.id (string) for deletion
                    list.innerHTML += `
                        <div class="char-card" ${clickAction} style="${cursorStyle}">
                            <img src="${c.profile_picture_url}" class="char-avatar">
                            <div class="char-info">
                                <div class="char-name">${name}</div>
                                <div class="char-id">ID: ${c.id}</div>
                            </div>
                            <div class="char-actions">
                                <button class="btn-sm btn-delete" onclick="event.stopPropagation(); deleteCharacter('${c.id}')">删除</button>
                            </div>
                        </div>
                    `;
                });
            } catch (e) {
                console.error("Failed to load characters", e);
                document.getElementById('my-char-list').innerHTML = '<div style="color:red; text-align:center;">加载失败</div>';
            }
        }

        async function deleteCharacter(id) {
            if(!confirm('确定要删除这个角色吗？(Are you sure?)')) return;
            try {
                const res = await fetch(`${API_BASE}/characters/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    loadCharacters();
                } else {
                    alert("删除失败");
                }
            } catch (e) {
                alert("删除出错: " + e.message);
            }
        }
        
        // Picker Logic
        let currentTargetInputId = null;

        async function openCharPicker(inputId) {
            currentTargetInputId = inputId;
            const modal = document.getElementById('charPickerModal');
            const list = document.getElementById('picker-list');
            
            try {
                const res = await fetch(`${API_BASE}/characters`);
                const chars = await res.json();
                
                list.innerHTML = '';
                if (chars.length === 0) {
                    list.innerHTML = '<div style="text-align:center; padding: 20px; color: #64748b;">暂无角色，请先去创建。</div>';
                } else {
                    chars.forEach(c => {
                        const name = c.name || c.username || 'Unknown';
                        const div = document.createElement('div');
                        div.className = 'char-card';
                        div.style.cursor = 'pointer';
                        div.onclick = () => selectCharacter(c);
                        div.innerHTML = `
                            <img src="${c.profile_picture_url}" class="char-avatar">
                            <div class="char-info">
                                <div class="char-name">${name}</div>
                                <div class="char-id">${c.id}</div>
                            </div>
                        `;
                        list.appendChild(div);
                    });
                }
                modal.classList.remove('hidden');
            } catch (e) {
                console.error(e);
                alert("加载角色列表失败");
            }
        }

        function closeCharPicker() {
            document.getElementById('charPickerModal').classList.add('hidden');
        }

        function selectCharacter(c) {
            // Unified selection logic
            // 1. Always insert text if input exists
            const input = document.getElementById(currentTargetInputId);
            if (input) {
                const val = input.value;
                const prefix = val.length > 0 && !val.endsWith(' ') ? ' ' : '';
                const handle = c.username || c.name || c.id;
                const textToInsert = `${prefix}@${handle} `; 
                input.value = val + textToInsert;
                input.focus();
            }

            // 2. If selecting for 'prompt' (Studio Mode), ALSO set the video reference
            if (currentTargetInputId === 'prompt') {
                const titleEl = document.getElementById('char-video-title');
                const display = document.getElementById('selected-char-display');
                const nameEl = document.getElementById('selected-char-name');
                const idEl = document.getElementById('selected-char-id');
                const imgEl = document.getElementById('selected-char-img');
                const urlInput = document.getElementById('charVideoUrl');
                const timeInput = document.getElementById('charVideoTimestamps');
                
                // Populate UI
                nameEl.textContent = c.name || c.username || 'Unknown Character';
                idEl.textContent = `ID: ${c.id}`;
                imgEl.src = c.profile_picture_url;
                
                // Show title and display
                if(titleEl) titleEl.style.display = 'block';
                display.style.display = 'flex';
                
                // Populate hidden inputs
                const videoUrl = c.url || c.video_url; 
                urlInput.value = videoUrl || '';
                timeInput.value = c.timestamps || '';
                
                if (!videoUrl) {
                    console.warn("Character has no direct URL property", c);
                }
            }
            
            closeCharPicker();
        }

        function clearSelectedCharacter() {
             const titleEl = document.getElementById('char-video-title');
             if(titleEl) titleEl.style.display = 'none';
             document.getElementById('selected-char-display').style.display = 'none';
             document.getElementById('charVideoUrl').value = '';
             document.getElementById('charVideoTimestamps').value = '';
        }

        // Initialize toggle
        function toggleCharSource() {
             const type = document.getElementById('ch-source-type').value;
             document.getElementById('group-url').classList.add('hidden');
             document.getElementById('group-file').classList.add('hidden');
             document.getElementById('group-task').classList.add('hidden');

             if (type === 'url') {
                 document.getElementById('group-url').classList.remove('hidden');
             } else if (type === 'file') {
                 document.getElementById('group-file').classList.remove('hidden');
             } else {
                 document.getElementById('group-task').classList.remove('hidden');
             }
        }
        
        function updateCharFileName(input) {
            const label = document.getElementById('ch-fileLabel');
            if (input.files && input.files.length > 0) {
                label.innerHTML = `<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">✅</span>${input.files[0].name}`;
            } else {
                label.innerHTML = '<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">📹</span>点击上传视频';
            }
        }

        function updateCharFileNameModal(input) {
            const label = document.getElementById('char-video-label-modal');
            if (input.files && input.files.length > 0) {
                label.innerHTML = `<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">✅</span>${input.files[0].name}`;
            } else {
                label.innerHTML = '<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">📹</span>点击上传视频';
            }
        }

        async function submitCharacterStandalone() {
            const timestamps = document.getElementById('ch-timestamps').value.trim();
            const sourceType = document.getElementById('ch-source-type').value;
            
            // UI Elements
            const btn = document.getElementById('createCharBtnStandalone');
            const resultDiv = document.getElementById('char-result-standalone');

            // Try to get API Key from this panel first, then main panel, then localStorage
            let apiKey = document.getElementById('ch-apiKey') ? document.getElementById('ch-apiKey').value : (document.getElementById('apiKey').value || localStorage.getItem('sora_api_key'));
            
            if (!apiKey) {
                alert("请输入 API Key！");
                return;
            }
            // Save to localStorage
            localStorage.setItem('sora_api_key', apiKey);

            if (!timestamps) {
                alert("请输入时间戳！");
                return;
            }
            
            // Validate timestamps (Duration 1-3s)
            const timeParts = timestamps.split(',').map(t => parseFloat(t.trim()));
            
            if (timeParts.length !== 2) {
                alert("请输入起始和结束时间，用逗号分隔！(例如: 1,3)");
                return;
            }
            
            if (timeParts.some(isNaN)) {
                 alert("时间戳格式不正确！");
                 return;
            }

            const start = timeParts[0];
            const end = timeParts[1];
            const duration = end - start;
            
            if (duration < 1 || duration > 3) {
                alert(`时间间隔必须在 1 到 3 秒之间！(当前: ${duration.toFixed(1)}秒)`);
                return;
            }
            
            let payload = {
                timestamps: timestamps,
                api_key: apiKey
            };

            const fileInput = document.getElementById('ch-fileInput');
            
            // Validation & Payload Construction based on Source Type
            if (sourceType === 'url') {
                const urlVal = document.getElementById('ch-video-url').value.trim();
                if (!urlVal) {
                    alert("请输入视频 URL！");
                    return;
                }
                payload.url = urlVal;
            } else if (sourceType === 'task') {
                const taskIdVal = document.getElementById('ch-task-id').value.trim();
                if (!taskIdVal) {
                    alert("请输入任务 ID！");
                    return;
                }
                payload.from_task = taskIdVal;
            } else if (sourceType === 'file') {
                if (!fileInput.files || fileInput.files.length === 0) {
                    alert("请上传视频文件！");
                    return;
                }
            }

            btn.disabled = true;
            resultDiv.style.display = 'none';
            
            try {
                // If file is selected (and source type is file), upload it first
                if (sourceType === 'file') {
                    btn.innerHTML = '🔄 上传视频中...';
                    
                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    
                    const upRes = await fetch(`${API_BASE}/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!upRes.ok) {
                        throw new Error("视频上传失败");
                    }
                    
                    const upData = await upRes.json();
                    // Construct full URL. API_BASE usually is http://localhost:8000 (or relative)
                    // If API_BASE is empty string (relative), we need window.location.origin
                    let baseUrl = API_BASE;
                    if (!baseUrl || baseUrl.startsWith('/')) {
                        baseUrl = window.location.origin + baseUrl;
                    }
                    payload.url = `${baseUrl}${upData.url}`;
                    
                    btn.innerHTML = '⏳ 创建中...';
                } else {
                    btn.innerHTML = '⏳ 创建中...';
                }
            
                const res = await fetch(`${API_BASE}/characters`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const data = await res.json();
                    
                    // --- Refresh Character List ---
                    loadCharacters();
                    // ----------------------
                    
                    resultDiv.innerHTML = `
                        <div style="color: #15803d; font-weight: bold; margin-bottom: 10px;">✅ 角色创建成功！(Saved to My Characters)</div>
                        <div style="display:flex; gap:15px; align-items: flex-start;">
                            <img src="${data.profile_picture_url}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #15803d;">
                            <div>
                                <div style="font-weight: 700; color: #1a2e05;">${data.username}</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary); margin: 5px 0;">ID: ${data.id}</div>
                                <a href="${data.permalink}" target="_blank" style="color: var(--primary-color); font-weight: 600; text-decoration: none;">🔗 查看角色主页</a>
                            </div>
                        </div>
                    `;
                    resultDiv.style.display = 'block';
                } else {
                    const err = await res.json();
                    resultDiv.innerHTML = `<div style="color: #ef4444;">❌ 创建失败: ${err.detail || "未知错误"}</div>`;
                    resultDiv.style.display = 'block';
                }
            } catch (e) {
                resultDiv.innerHTML = `<div style="color: #ef4444;">❌ 错误: ${e.message}</div>`;
                resultDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '👤 开始创建';
            }
        }
        
        // Initialize UI state
        toggleCharSource();

        function addScene() {
            sceneCount++;
            const id = sceneCount;
            const container = document.getElementById('storyboard-container');
            
            const div = document.createElement('div');
            div.className = 'storyboard-card';
            div.id = `scene-${id}`;
            div.innerHTML = `
                <div class="storyboard-header">
                    <div class="scene-badge">场景 ${id} (Scene ${id})</div>
                    <button class="remove-scene-btn" onclick="removeScene(${id})" title="删除场景">×</button>
                </div>
                <div class="input-group">
                    <label>本场景时长 (Duration)</label>
                    <input type="number" id="scene-duration-${id}" step="0.1" min="0.1" value="3.0" onchange="updateRemainingTime()" placeholder="e.g. 2.5">
                </div>
                <div class="input-group">
                    <label>场景描述 (Prompt)
                        <button onclick="openCharPicker('scene-prompt-${id}')" style="float: right; font-size: 0.8rem; padding: 4px 10px; background: #e0f2fe; color: #0284c7; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">+ 插入角色</button>
                    </label>
                    <textarea id="scene-prompt-${id}" placeholder="描述这个场景发生的故事..."></textarea>
                </div>
            `;
            container.appendChild(div);

            // Init custom selects for new elements
            // setupCustomSelect(document.getElementById(`scene-duration-${id}`)); // Input type doesn't need custom select
            
            updateRemainingTime();
        }

        function removeScene(id) {
            const el = document.getElementById(`scene-${id}`);
            if (el) el.remove();
            updateRemainingTime();
        }
        
        function updateRemainingTime() {
            const totalDuration = parseFloat(document.getElementById('sb-total-duration').value) || 10;
            let usedDuration = 0;
            
            document.querySelectorAll('[id^="scene-duration-"]').forEach(el => {
                usedDuration += parseFloat(el.value) || 0;
            });
            
            // Fix float precision issues
            usedDuration = Math.round(usedDuration * 10) / 10;
            const remaining = Math.round((totalDuration - usedDuration) * 10) / 10;
            
            const remainingEl = document.getElementById('time-remaining');
            
            if (remaining < 0) {
                remainingEl.textContent = `${remaining}s (超出!)`;
                remainingEl.style.color = '#ef4444';
            } else {
                remainingEl.textContent = `${remaining}s`;
                remainingEl.style.color = 'var(--primary-color)';
            }
        }
        
        function updateSbFileName(input) {
            const label = document.getElementById('sb-fileLabel');
            if (input.files && input.files[0]) {
                label.innerHTML = `<span style="color: #4ade80">✓ ${input.files[0].name}</span>`;
            } else {
                label.innerHTML = '<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">🖼️</span>点击上传首帧图片';
            }
        }

        async function submitStoryboard() {
            const apiKey = document.getElementById('sb-apiKey').value.trim();
            const model = document.getElementById('sb-model').value;
            const totalDuration = parseInt(document.getElementById('sb-total-duration').value);
            const orientation = document.getElementById('sb-orientation').value;
            const imageInput = document.getElementById('sb-imageInput');
            const submitBtn = document.getElementById('sb-submitBtn');

            if (!apiKey) {
                alert("请输入 API Key！");
                return;
            }
            
            // Collect all scenes
            const sceneCards = document.querySelectorAll('.storyboard-card');
            if (sceneCards.length === 0) {
                alert("请至少添加一个场景！");
                return;
            }

            // Calculate prompt and validation
            let scenes = [];
            let calculatedDuration = 0;
            let hasPrompt = false;

            for (const card of sceneCards) {
                const idStr = card.id.replace('scene-', '');
                const prompt = document.getElementById(`scene-prompt-${idStr}`).value.trim();
                const duration = parseFloat(document.getElementById(`scene-duration-${idStr}`).value);
                
                if (prompt) hasPrompt = true;
                
                scenes.push({
                    duration: duration,
                    prompt: prompt || "Continue previous action"
                });
                calculatedDuration += duration;
            }

            // Fix precision before comparing
            calculatedDuration = Math.round(calculatedDuration * 10) / 10;
            const diff = Math.abs(calculatedDuration - totalDuration);

            if (diff > 0.1) { // Allow slight epsilon, though rounding should handle it
                alert(`时间分配错误！\n总时长: ${totalDuration}s\n分镜总和: ${calculatedDuration}s\n请调整分镜时长使总和等于总时长。`);
                return;
            }
            
            if (!hasPrompt) {
                alert("请至少为一个场景填写描述！");
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '⏳ 正在提交...';

            try {
                let imageBase64 = null;
                if (imageInput && imageInput.files.length > 0) {
                    const file = imageInput.files[0];
                    if (file.size > 10 * 1024 * 1024) {
                         alert("参考图过大 (Max 10MB)");
                         submitBtn.disabled = false;
                         return;
                    }
                    imageBase64 = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.onerror = error => reject(error);
                        reader.readAsDataURL(file);
                    });
                }

                // Size mapping for backend
                let size = "large"; // Default to large, backend uses orientation to determine resolution

                // Submit single task
                const res = await fetch(`${API_BASE}/tasks`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        prompt: "", // Backend will construct it from scenes
                        api_key: apiKey,
                        duration: totalDuration,
                        model: model,
                        size: size,
                        orientation: orientation,
                        image: imageBase64,
                        mode: 'storyboard',
                        scenes: scenes
                    })
                });

                if (res.ok) {
                    refresh();
                    alert("故事板任务提交成功！");
                    // Reset UI? Maybe not to allow edits
                } else {
                    const err = await res.json();
                    alert(`提交失败: ${err.detail || "未知错误"}`);
                }
            } catch (e) {
                alert(`网络错误: ${e.message}`);
            }

            submitBtn.disabled = false;
            submitBtn.innerHTML = '🚀 生成视频 (Generate Video)';
        }

        function updateFileName(input) {
            const label = document.getElementById('fileLabel');
            if (input.files && input.files[0]) {
                label.innerHTML = `<span style="color: #4ade80">✓ ${input.files[0].name}</span>`;
            } else {
                label.innerHTML = '<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">🖼️</span>点击上传图片';
            }
        }

        function updateSceneFileName(input, id) {
            const label = document.getElementById(`scene-fileLabel-${id}`);
            if (input.files && input.files[0]) {
                label.innerHTML = `<span style="color: #4ade80">✓ ${input.files[0].name}</span>`;
            } else {
                label.innerHTML = '<span style="font-size: 1.5rem; display: block; margin-bottom: 5px;">🖼️</span>点击上传图片';
            }
        }

        // 从 localStorage 加载 API Key 并设置同步
        document.addEventListener('DOMContentLoaded', () => {
            const savedKey = localStorage.getItem('sora_api_key');
            
            const apiKeyInputs = [
                document.getElementById('apiKey'),
                document.getElementById('sb-apiKey'),
                document.getElementById('ch-apiKey')
            ];

            // 初始加载
            if (savedKey) {
                apiKeyInputs.forEach(input => {
                    if (input) input.value = savedKey;
                });
            }

            // 同步输入
            apiKeyInputs.forEach(input => {
                if (input) {
                    input.addEventListener('input', (e) => {
                        const newVal = e.target.value;
                        localStorage.setItem('sora_api_key', newVal);
                        apiKeyInputs.forEach(otherInput => {
                            if (otherInput && otherInput !== input) {
                                otherInput.value = newVal;
                            }
                        });
                    });
                }
            });

            // Initialize custom selects
            initCustomSelects();
        });

        // Custom Select Implementation
        function initCustomSelects() {
            const selects = document.querySelectorAll('select:not(.custom-select-hidden)');
            selects.forEach(select => {
                setupCustomSelect(select);
            });

            // Close when clicking outside
            window.addEventListener('click', (e) => {
                if (!e.target.closest('.custom-select')) {
                    document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open'));
                }
            });
        }

        function setupCustomSelect(select) {
            if (!select || select.classList.contains('custom-select-hidden')) return;
            
            // Hide original
            select.classList.add('custom-select-hidden');
            select.style.display = 'none';

            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.classList.add('custom-select-wrapper');
            select.parentNode.insertBefore(wrapper, select);
            wrapper.appendChild(select);

            const customSelect = document.createElement('div');
            customSelect.classList.add('custom-select');
            wrapper.appendChild(customSelect);

            // Create trigger
            const trigger = document.createElement('div');
            trigger.classList.add('custom-select__trigger');
            
            // Initial text
            const selectedOption = select.options[select.selectedIndex];
            trigger.innerHTML = `<span>${selectedOption ? selectedOption.text : 'Select...'}</span>`;
            
            const arrow = document.createElement('div');
            arrow.classList.add('arrow');
            trigger.appendChild(arrow);
            
            customSelect.appendChild(trigger);

            // Create options container
            const optionsDiv = document.createElement('div');
            optionsDiv.classList.add('custom-options');
            
            // Populate options
            Array.from(select.options).forEach(option => {
                const optionDiv = document.createElement('div');
                optionDiv.classList.add('custom-option');
                optionDiv.dataset.value = option.value;
                optionDiv.textContent = option.text;
                
                if (option.selected) {
                    optionDiv.classList.add('selected');
                }

                optionDiv.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent bubbling
                    
                    // Update visual selection
                    optionsDiv.querySelectorAll('.custom-option').forEach(el => el.classList.remove('selected'));
                    optionDiv.classList.add('selected');
                    
                    // Update trigger text
                    trigger.querySelector('span').textContent = option.text;
                    
                    // Update native select
                    select.value = option.value;
                    // Trigger native change event if needed
                    const event = new Event('change');
                    select.dispatchEvent(event);
                    
                    // Close dropdown
                    customSelect.classList.remove('open');
                });
                
                optionsDiv.appendChild(optionDiv);
            });
            
            customSelect.appendChild(optionsDiv);

            // Toggle open
            trigger.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent closing immediately via window click
                
                // Close others
                document.querySelectorAll('.custom-select').forEach(el => {
                    if (el !== customSelect) el.classList.remove('open');
                });
                customSelect.classList.toggle('open');
            });
        }

        async function createTask() {
            const promptInput = document.getElementById("prompt");
            const charVideoUrlInput = document.getElementById("charVideoUrl");
            const charVideoTimestampsInput = document.getElementById("charVideoTimestamps");
            const apiKeyInput = document.getElementById("apiKey");
            const durationInput = document.getElementById("duration");
            const modelInput = document.getElementById("model");
            const sizeInput = document.getElementById("size");
            const orientationInput = document.getElementById("orientation");
            const imageInput = document.getElementById("imageInput");
            const submitBtn = document.getElementById("submitBtn");

            const prompt = promptInput.value.trim();
            const apiKey = apiKeyInput.value.trim();
            const duration = parseInt(durationInput.value);
            const model = modelInput.value;
            const size = sizeInput.value;
            const orientation = orientationInput.value;
            const charVideoUrl = charVideoUrlInput.value.trim();
            const charVideoTimestamps = charVideoTimestampsInput.value.trim();

            if (!prompt && imageInput.files.length === 0 && !charVideoUrl) {
                alert("请填写创意描述、上传参考图或填写角色视频URL！");
                return;
            }

            if (!apiKey) {
                alert("请输入 API Key！");
                return;
            }

            // 保存 API Key 到本地
            if (apiKey) {
                localStorage.setItem('sora_api_key', apiKey);
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="status-running">🚀</span> 正在提交...';

            try {
                let imageBase64 = null;
                if (imageInput.files.length > 0) {
                    const file = imageInput.files[0];
                    if (file.size > 10 * 1024 * 1024) { // 10MB
                        alert("图片大小不能超过 10MB");
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '✨ 开始生成';
                        return;
                    }

                    // 如果图片大于 2MB，进行压缩
                    if (file.size > 2 * 1024 * 1024) {
                        submitBtn.innerHTML = '🔄 正在处理图片...';
                        imageBase64 = await compressImage(file);
                    } else {
                        // 直接读取
                        imageBase64 = await new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onload = () => resolve(reader.result);
                            reader.onerror = error => reject(error);
                            reader.readAsDataURL(file);
                        });
                    }
                    submitBtn.innerHTML = '🚀 正在提交...';
                }

                const res = await fetch(`${API_BASE}/tasks`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        prompt: prompt,
                        api_key: apiKey || null,
                        duration: duration,
                        model: model,
                        size: size,
                        orientation: orientation,
                        image: imageBase64,
                        mode: 'studio',
                        character_url: charVideoUrl || null,
                        character_timestamps: charVideoTimestamps || null
                    })
                });
                
                if (res.ok) {
                    promptInput.value = "";
                    imageInput.value = ""; // 清空文件选择
                    charVideoUrlInput.value = "";
                    charVideoTimestampsInput.value = "";
                    clearSelectedCharacter(); // 重置角色选择UI
                    updateFileName(imageInput); // 重置显示
                    refresh(); // 立即刷新列表
                } else {
                    const err = await res.json();
                    alert("提交失败: " + (err.detail || "未知错误"));
                }
            } catch (e) {
                console.error(e);
                alert("网络错误: " + e.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '✨ 开始生成';
            }
        }

        function compressImage(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = (event) => {
                    const img = new Image();
                    img.src = event.target.result;
                    img.onload = () => {
                        const canvas = document.createElement('canvas');
                        let width = img.width;
                        let height = img.height;
                        const MAX_SIZE = 2048;

                        if (width > MAX_SIZE || height > MAX_SIZE) {
                            if (width > height) {
                                height *= MAX_SIZE / width;
                                width = MAX_SIZE;
                            } else {
                                width *= MAX_SIZE / height;
                                height = MAX_SIZE;
                            }
                        }

                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        // 压缩为 JPEG，质量 0.8
                        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
                        resolve(dataUrl);
                    };
                    img.onerror = (err) => reject(err);
                };
                reader.onerror = (err) => reject(err);
            });
        }

        async function refresh() {
            try {
                const res = await fetch(`${API_BASE}/tasks`);
                const tasks = await res.json();
                renderTasks(tasks);
            } catch (e) {
                console.error("刷新任务失败:", e);
            }
        }

        async function deleteTask(taskId) {
            if(!confirm('确定要删除这个作品吗？(Are you sure?)')) return;
            try {
                const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
                if (res.ok) {
                    refresh();
                } else {
                    const err = await res.json();
                    alert("删除失败: " + (err.detail || "未知错误"));
                }
            } catch(e) {
                alert("删除出错: " + e.message);
            }
        }

        function renderTasks(tasks) {
            const container = document.getElementById("taskList");
            const sortedTasks = [...tasks].reverse();
            
            container.innerHTML = sortedTasks.map(task => {
                let statusClass = `status-${task.status}`;
                let mediaContent = '';
                let statusText = task.status;
                
                // Ensure task.id is treated as string for the button
                const taskIdStr = String(task.id);

                if (task.status === 'done' && task.result_path) {
                    const filename = task.result_path.split(/[/\\]/).pop();
                    const videoUrl = `${API_BASE}/outputs/${filename}`;
                    mediaContent = `
                        <video class="video-preview" controls>
                            <source src="${videoUrl}" type="video/mp4">
                            您的浏览器不支持 Video 标签
                        </video>
                        <div style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap;">
                             <a href="${videoUrl}" download class="download-btn" style="flex:1; text-align:center;">⬇️ 下载</a>
                             <button onclick="openCharacterModal('${taskIdStr}')" class="char-btn" style="flex:1;">👤 创建角色</button>
                        </div>
                    `;
                    statusText = "完成";
                } else if (task.status === 'failed') {
                    mediaContent = `<div class="error-msg" style="margin-top:10px; padding:10px; background:rgba(239,68,68,0.1); border-radius:8px;">❌ 失败: ${task.error || '未知错误'}</div>`;
                    statusText = "失败";
                } else {
                    mediaContent = `
                        <div class="progress-container">
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#94a3b8; margin-bottom:5px;">
                                <span>渲染中...</span>
                                <span>${task.progress}%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${task.progress}%"></div>
                            </div>
                        </div>
                    `;
                    statusText = "渲染中";
                }

                return `
                    <div class="task-card">
                        <div class="task-header">
                            <span class="task-id">#${task.id.slice(-6)}</span>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="status-badge ${statusClass}">${statusText}</span>
                                <button onclick="deleteTask('${taskIdStr}')" style="background:none; border:none; cursor:pointer; font-size:1.2rem; padding:0; line-height:1; opacity: 0.6; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6" title="删除">🗑️</button>
                            </div>
                        </div>
                        
                        <div class="task-meta">
                            <div class="meta-item">⏱️ ${task.duration}s</div>
                            <div class="meta-item">📐 ${task.resolution}</div>
                            ${task.has_image ? '<div class="meta-item">🖼️ 图生视</div>' : ''}
                        </div>

                        <div class="prompt-text" title="${task.prompt}">${task.prompt}</div>
                        ${mediaContent}
                    </div>
                `;
            }).join("");
        }

        setInterval(refresh, 2000);
        refresh();

        // Character Modal Logic
        function openCharacterModal(taskId) {
            const modal = document.getElementById('characterModal');
            document.getElementById('char-task-id').value = taskId;
            document.getElementById('char-result').style.display = 'none';
            document.getElementById('char-result').innerHTML = '';
            modal.classList.remove('hidden');
        }

        function closeCharacterModal() {
            document.getElementById('characterModal').classList.add('hidden');
        }

        async function submitCharacter() {
            const taskId = document.getElementById('char-task-id').value;
            const timestamps = document.getElementById('char-timestamps').value.trim();
            const videoInput = document.getElementById('char-video-upload-modal');
            const btn = document.getElementById('createCharBtn');
            const resultDiv = document.getElementById('char-result');
            
            // Get API Key from main input or localStorage
            let apiKey = document.getElementById('apiKey').value || localStorage.getItem('sora_api_key');
            if (!apiKey) {
                alert("请先在主界面输入 API Key！");
                return;
            }

            if (!timestamps) {
                alert("请输入时间戳！");
                return;
            }
            
            // Validate timestamps (Duration 1-3s)
            const timeParts = timestamps.split(',').map(t => parseFloat(t.trim()));
            
            if (timeParts.length !== 2) {
                alert("请输入起始和结束时间，用逗号分隔！(例如: 1,3)");
                return;
            }
            
            if (timeParts.some(isNaN)) {
                 alert("时间戳格式不正确！");
                 return;
            }

            const start = timeParts[0];
            const end = timeParts[1];
            const duration = end - start;
            
            if (duration < 1 || duration > 3) {
                alert(`时间间隔必须在 1 到 3 秒之间！(当前: ${duration.toFixed(1)}秒)`);
                return;
            }
            
            // Check if file is uploaded or task ID exists
            if (!taskId && (!videoInput || !videoInput.files || videoInput.files.length === 0)) {
                 alert("请选择一个任务或上传一个视频！");
                 return;
            }

            btn.disabled = true;
            btn.innerHTML = '⏳ 创建中...';
            resultDiv.style.display = 'none';

            try {
                let payload = {
                    timestamps: timestamps,
                    api_key: apiKey
                };
                
                // If file is selected, upload it first
                if (videoInput && videoInput.files && videoInput.files.length > 0) {
                     btn.innerHTML = '🔄 上传视频中...';
                     const formData = new FormData();
                     formData.append("file", videoInput.files[0]);
                     
                     const uploadRes = await fetch(`${API_BASE}/upload`, {
                         method: "POST",
                         body: formData
                     });
                     
                     if (!uploadRes.ok) throw new Error("Video upload failed");
                     const uploadData = await uploadRes.json();
                     
                     let baseUrl = API_BASE;
                     if (!baseUrl || baseUrl.startsWith('/')) {
                         baseUrl = window.location.origin + baseUrl;
                     }
                     payload.url = `${baseUrl}${uploadData.url}`;
                } else {
                     payload.from_task = taskId;
                }

                btn.innerHTML = '⏳ 创建中...';

                const res = await fetch(`${API_BASE}/characters`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(payload)
                });
                
                if (res.ok) {
                    const data = await res.json();
                    
                    loadCharacters(); // Refresh list
                    
                    resultDiv.innerHTML = `
                        <div style="color: green; font-weight: bold; margin-bottom: 10px;">✅ 角色创建成功！</div>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <img src="${data.profile_picture_url}" style="width: 50px; height: 50px; border-radius: 50%;">
                            <div>
                                <div><b>Username:</b> ${data.username}</div>
                                <div><b>ID:</b> ${data.id}</div>
                                <a href="${data.permalink}" target="_blank" style="color: #0284c7;">Open in OpenAI</a>
                            </div>
                        </div>
                    `;
                    resultDiv.style.display = 'block';
                } else {
                    const err = await res.json();
                    throw new Error(err.detail || "Creation failed");
                }
            } catch (e) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div style="color: red;">❌ ${e.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '开始创建';
            }
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('characterModal');
            if (event.target == modal) {
                closeCharacterModal();
            }
        }