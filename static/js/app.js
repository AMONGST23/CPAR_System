(function () {
  const SYNC_DB_NAME = 'cpar-offline-sync';
  const SYNC_STORE_NAME = 'queued-records';
  const excludedFields = new Set(['csrfmiddlewaretoken']);

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/static/js/service-worker.js').catch(function (error) {
        console.error('Service worker registration failed:', error);
      });
    });
  }

  function setText(element, message) {
    if (element) {
      element.textContent = message;
    }
  }

  function setAlert(alert, message, variant) {
    if (!alert) {
      return;
    }

    alert.textContent = message;
    alert.className = 'alert';
    alert.classList.add(variant ? 'alert--' + variant : 'alert--success');
    alert.classList.remove('hidden');
  }

  function storeSessionMessage(message, variant) {
    try {
      window.sessionStorage.setItem('cpar-sync-message', JSON.stringify({
        message: message,
        variant: variant || 'warning'
      }));
    } catch (error) {
      console.error('Failed to store session message:', error);
    }
  }

  function restoreStoredSyncMessage(statusAlert) {
    if (!statusAlert) {
      return;
    }

    try {
      const rawMessage = window.sessionStorage.getItem('cpar-sync-message');
      if (!rawMessage) {
        return;
      }

      window.sessionStorage.removeItem('cpar-sync-message');
      const parsed = JSON.parse(rawMessage);
      setAlert(statusAlert, parsed.message, parsed.variant || 'warning');
    } catch (error) {
      console.error('Failed to restore sync message:', error);
    }
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split(';')
      .map(function (item) { return item.trim(); })
      .find(function (item) { return item.startsWith(name + '='); });

    return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
  }

  function generateSyncUuid() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }

    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (character) {
      const random = Math.random() * 16 | 0;
      const value = character === 'x' ? random : (random & 0x3 | 0x8);
      return value.toString(16);
    });
  }

  function getUrlParams() {
    return new URLSearchParams(window.location.search);
  }

  function buildCreateUrl(baseUrl, syncUuid, section) {
    const url = new URL(baseUrl, window.location.origin);
    url.searchParams.set('offline_record', syncUuid);
    if (section) {
      url.searchParams.set('section', section);
    }
    return url.pathname + url.search;
  }

  function sectionLabel(sectionId) {
    const labels = {
      'sec-a': 'A. Respondent',
      'sec-b': 'B. Obstetric History',
      'sec-c': 'C. Current Pregnancy',
      'sec-d': 'D. Health Assessment',
      'sec-e': 'E. Services',
      'sec-f': 'F. Ultrasound & Referral',
      'sec-g': 'G. GBV Response',
      'sec-h': 'H. Nutrition, FP & STI',
      'sec-i': 'I. Client Experience'
    };
    return labels[sectionId] || sectionId || 'Unknown';
  }

  function localStatusLabel(status) {
    const labels = {
      draft: 'Draft on device',
      pending_sync: 'Pending sync',
      syncing: 'Syncing',
      sync_failed: 'Sync failed'
    };
    return labels[status] || status;
  }

  function isSyncableStatus(status) {
    return status === 'pending_sync' || status === 'sync_failed';
  }

  function openSyncDatabase() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) {
        reject(new Error('IndexedDB is not available.'));
        return;
      }

      const request = window.indexedDB.open(SYNC_DB_NAME, 1);

      request.onerror = function () {
        reject(request.error || new Error('Failed to open the sync database.'));
      };

      request.onupgradeneeded = function () {
        const database = request.result;
        if (!database.objectStoreNames.contains(SYNC_STORE_NAME)) {
          database.createObjectStore(SYNC_STORE_NAME, { keyPath: 'sync_uuid' });
        }
      };

      request.onsuccess = function () {
        resolve(request.result);
      };
    });
  }

  function withSyncStore(mode, callback) {
    return openSyncDatabase().then(function (database) {
      return new Promise(function (resolve, reject) {
        const transaction = database.transaction(SYNC_STORE_NAME, mode);
        const store = transaction.objectStore(SYNC_STORE_NAME);
        const request = callback(store);

        transaction.oncomplete = function () {
          database.close();
          resolve(request ? request.result : undefined);
        };

        transaction.onerror = function () {
          database.close();
          reject(transaction.error || new Error('IndexedDB transaction failed.'));
        };

        transaction.onabort = function () {
          database.close();
          reject(transaction.error || new Error('IndexedDB transaction aborted.'));
        };
      });
    });
  }

  function normalizeLocalRecord(entry) {
    const payload = entry && entry.payload ? entry.payload : {};
    return {
      sync_uuid: entry.sync_uuid || payload.sync_uuid || generateSyncUuid(),
      local_id: entry.local_id || (entry.sync_uuid || payload.sync_uuid || generateSyncUuid()).slice(0, 8),
      status: entry.status || 'draft',
      current_section: entry.current_section || 'sec-a',
      payload: payload,
      createdAt: entry.createdAt || new Date().toISOString(),
      updatedAt: entry.updatedAt || new Date().toISOString(),
      lastAttemptAt: entry.lastAttemptAt || null,
      error: entry.error || ''
    };
  }

  function putLocalRecord(record) {
    return withSyncStore('readwrite', function (store) {
      return store.put(normalizeLocalRecord(record));
    });
  }

  function deleteLocalRecord(syncUuid) {
    return withSyncStore('readwrite', function (store) {
      return store.delete(syncUuid);
    });
  }

  function getAllLocalRecords() {
    return withSyncStore('readonly', function (store) {
      return store.getAll();
    }).then(function (entries) {
      return (entries || []).map(normalizeLocalRecord).sort(function (first, second) {
        return new Date(second.updatedAt).getTime() - new Date(first.updatedAt).getTime();
      });
    });
  }

  function getLocalRecord(syncUuid) {
    return withSyncStore('readonly', function (store) {
      return store.get(syncUuid);
    }).then(function (entry) {
      return entry ? normalizeLocalRecord(entry) : null;
    });
  }

  function countSyncableRecords() {
    return getAllLocalRecords().then(function (entries) {
      return entries.filter(function (entry) {
        return isSyncableStatus(entry.status);
      }).length;
    });
  }

  function getSectionSequence() {
    return Array.from(document.querySelectorAll('.tab[data-tab]')).map(function (tab) {
      return tab.dataset.tab;
    });
  }

  function getNextSection(currentSection) {
    const sequence = getSectionSequence();
    const index = sequence.indexOf(currentSection);
    if (index === -1 || index >= sequence.length - 1) {
      return currentSection;
    }
    return sequence[index + 1];
  }

  function serializeFormValues(form) {
    const payload = {};
    const elements = form.querySelectorAll('input, select, textarea');

    elements.forEach(function (field) {
      if (!field.name || field.disabled || excludedFields.has(field.name)) {
        return;
      }

      if (field.type === 'checkbox') {
        payload[field.name] = field.checked;
        return;
      }

      if (field.type === 'radio') {
        if (!(field.name in payload)) {
          payload[field.name] = '';
        }

        if (field.checked) {
          payload[field.name] = field.value;
        }
        return;
      }

      payload[field.name] = field.value;
    });

    return payload;
  }

  function applyValuesToForm(form, values) {
    Object.entries(values || {}).forEach(function (entry) {
      const name = entry[0];
      const value = entry[1];
      const field = form.elements.namedItem(name);

      if (!field || excludedFields.has(name)) {
        return;
      }

      if (field instanceof RadioNodeList) {
        Array.from(field).forEach(function (option) {
          option.checked = option.value === String(value);
        });
        return;
      }

      if (field.type === 'checkbox') {
        field.checked = Boolean(value);
        return;
      }

      field.value = value == null ? '' : value;
    });
  }

  function buildLocalRecord(payload, options) {
    const settings = options || {};
    const now = new Date().toISOString();
    const existing = settings.existing || {};
    return normalizeLocalRecord({
      sync_uuid: payload.sync_uuid,
      local_id: existing.local_id || payload.sync_uuid.slice(0, 8),
      status: settings.status || existing.status || 'draft',
      current_section: settings.currentSection || existing.current_section || 'sec-a',
      payload: payload,
      createdAt: existing.createdAt || now,
      updatedAt: now,
      lastAttemptAt: existing.lastAttemptAt || null,
      error: settings.error || ''
    });
  }

  function summarizeLocalRecord(record) {
    const payload = record.payload || {};
    const firstName = payload.first_name || 'Unnamed';
    const lastName = payload.last_name || 'Record';
    return {
      localId: record.local_id,
      name: lastName + ', ' + firstName,
      dateCollected: payload.date_collected || '-',
      currentSection: sectionLabel(record.current_section),
      status: localStatusLabel(record.status),
      syncUuid: record.sync_uuid
    };
  }

  async function renderLocalRecords() {
    const container = document.querySelector('[data-local-records-container]');
    const summary = document.querySelector('[data-local-records-summary]');
    const body = document.querySelector('[data-local-records-body]');

    if (!container || !summary || !body) {
      return;
    }

    const createUrl = container.dataset.createUrl || '/surveys/new/';
    let records = [];

    try {
      records = await getAllLocalRecords();
    } catch (error) {
      console.error('Failed to load local records:', error);
      summary.textContent = 'Offline device records are unavailable.';
      container.classList.remove('hidden');
      body.innerHTML = '<tr><td colspan="6">Could not read saved device records.</td></tr>';
      return;
    }

    if (!records.length) {
      container.classList.add('hidden');
      body.innerHTML = '';
      return;
    }

    container.classList.remove('hidden');
    summary.textContent = records.length + ' record' + (records.length === 1 ? '' : 's') + ' currently saved on this device.';

    body.innerHTML = records.map(function (record) {
      const details = summarizeLocalRecord(record);
      const continueUrl = buildCreateUrl(createUrl, record.sync_uuid, record.current_section);
      return '' +
        '<tr>' +
          '<td>' + details.localId + '</td>' +
          '<td><strong>' + details.name + '</strong></td>' +
          '<td>' + details.dateCollected + '</td>' +
          '<td>' + details.currentSection + '</td>' +
          '<td>' + details.status + '</td>' +
          '<td class="actions">' +
            '<a href="' + continueUrl + '" class="btn btn--sm btn--outline">Continue</a>' +
          '</td>' +
        '</tr>';
    }).join('');
  }

  async function updatePendingSyncCount() {
    const countElement = document.querySelector('[data-pending-sync-count]');
    const syncButton = document.querySelector('[data-sync-now]');

    try {
      const pendingCount = await countSyncableRecords();

      if (countElement) {
        if (pendingCount === 0) {
          setText(countElement, 'All synced.');
        } else {
          setText(countElement, pendingCount + ' record' + (pendingCount === 1 ? '' : 's') + ' waiting to sync.');
        }
      }

      if (syncButton) {
        if (pendingCount === 0) {
          syncButton.disabled = true;
          syncButton.textContent = 'All Synced';
        } else {
          syncButton.disabled = false;
          syncButton.textContent = 'Sync Now (' + pendingCount + ')';
        }
      }
    } catch (error) {
      console.error('Failed to read queued sync records:', error);
      if (countElement) {
        setText(countElement, 'Offline queue unavailable.');
      }
      if (syncButton) {
        syncButton.disabled = true;
      }
    }
  }

  async function refreshLocalSyncUi() {
    await Promise.all([
      updatePendingSyncCount(),
      renderLocalRecords()
    ]);
  }

  async function syncQueuedRecords(syncUrl, statusAlert, options) {
    const settings = options || {};
    if (!syncUrl) {
      return { synced: 0, failed: 0 };
    }

    let queuedEntries = [];
    try {
      queuedEntries = await getAllLocalRecords();
    } catch (error) {
      console.error('Unable to open offline queue:', error);
      if (!settings.silent) {
        setAlert(statusAlert, 'Offline queue is unavailable on this device.', 'error');
      }
      return { synced: 0, failed: 0 };
    }

    const pendingEntries = queuedEntries.filter(function (entry) {
      return isSyncableStatus(entry.status);
    });

    if (!pendingEntries.length) {
      await refreshLocalSyncUi();
      if (!settings.silent && statusAlert) {
        setAlert(statusAlert, 'All device-saved records are already synced.', 'success');
      }
      return { synced: 0, failed: 0 };
    }

    if (!navigator.onLine) {
      if (!settings.silent && statusAlert) {
        setAlert(statusAlert, 'No connection. Pending device records will sync when you are back online.', 'warning');
      }
      return { synced: 0, failed: pendingEntries.length };
    }

    const csrfToken = getCookie('csrftoken');
    let syncedCount = 0;
    let failedCount = 0;

    for (const entry of pendingEntries) {
      await putLocalRecord(Object.assign({}, entry, {
        status: 'syncing',
        lastAttemptAt: new Date().toISOString(),
        error: ''
      }));

      try {
        const response = await fetch(syncUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify(entry.payload)
        });

        if (!response.ok) {
          let errorMessage = 'Server rejected the record.';
          try {
            const data = await response.json();
            errorMessage = data.detail || JSON.stringify(data);
          } catch (error) {
            errorMessage = 'Server rejected the record.';
          }

          await putLocalRecord(Object.assign({}, entry, {
            status: 'sync_failed',
            lastAttemptAt: new Date().toISOString(),
            error: errorMessage
          }));
          failedCount += 1;
          continue;
        }

        await deleteLocalRecord(entry.sync_uuid);
        syncedCount += 1;
      } catch (error) {
        await putLocalRecord(Object.assign({}, entry, {
          status: 'sync_failed',
          lastAttemptAt: new Date().toISOString(),
          error: error.message || 'Network error while syncing.'
        }));
        failedCount += 1;
        break;
      }
    }

    await refreshLocalSyncUi();

    if (statusAlert && !settings.silent) {
      if (failedCount && syncedCount) {
        setAlert(statusAlert, syncedCount + ' record(s) synced. ' + failedCount + ' still need attention.', 'warning');
      } else if (failedCount) {
        setAlert(statusAlert, 'Sync did not finish. Pending records remain on this device.', 'error');
      } else {
        setAlert(statusAlert, syncedCount + ' queued record(s) synced successfully.', 'success');
      }
    }

    return { synced: syncedCount, failed: failedCount };
  }

  function initializeListSync() {
    const syncButton = document.querySelector('[data-sync-now]');
    const statusAlert = document.getElementById('sync-status');
    const syncUrl = syncButton ? syncButton.dataset.syncUrl : '';

    refreshLocalSyncUi();
    restoreStoredSyncMessage(statusAlert);

    if (!syncButton) {
      return;
    }

    syncButton.addEventListener('click', function () {
      syncQueuedRecords(syncUrl, statusAlert, { silent: false });
    });

    window.addEventListener('online', function () {
      syncQueuedRecords(syncUrl, statusAlert, { silent: true }).then(function (result) {
        if (result.synced > 0 && statusAlert) {
          setAlert(statusAlert, result.synced + ' device-saved record(s) synced after reconnect.', 'success');
        }
      });
    });

    if (navigator.onLine) {
      syncQueuedRecords(syncUrl, statusAlert, { silent: true });
    }
  }

  function initializeSurveyForm() {
    const surveyForm = document.querySelector('[data-draft-key]');
    const draftStatus = document.querySelector('[data-draft-status]');
    const clearDraftButton = document.querySelector('[data-clear-draft]');
    const currentSectionInput = document.getElementById('current-section-input');
    const submitActionInput = document.getElementById('submit-action-input');

    if (!surveyForm || !currentSectionInput || !submitActionInput) {
      return;
    }

    const params = getUrlParams();
    const requestedOfflineRecord = params.get('offline_record');
    const requestedSection = params.get('section');
    const draftKeyBase = surveyForm.dataset.draftKey;
    const isEditMode = surveyForm.dataset.recordMode === 'edit';
    const listUrl = surveyForm.dataset.listUrl || '/surveys/';
    const createUrl = surveyForm.dataset.createUrl || '/surveys/new/';
    const syncUuidInput = surveyForm.querySelector('#sync-uuid-input');
    const storage = window.localStorage;
    let submissionInFlight = false;
    let localRecord = null;

    function setDraftStatus(message) {
      setText(draftStatus, message);
    }

    function getDraftKey() {
      return draftKeyBase + '-' + (syncUuidInput && syncUuidInput.value ? syncUuidInput.value : 'new');
    }

    function saveDraft() {
      const payload = serializeFormValues(surveyForm);

      storage.setItem(getDraftKey(), JSON.stringify({
        updatedAt: new Date().toISOString(),
        values: payload
      }));

      setDraftStatus('Draft saved on this device.');
    }

    function restoreDraft() {
      if (isEditMode) {
        setDraftStatus('Draft protection is disabled while editing an existing record.');
        return;
      }

      const rawDraft = storage.getItem(getDraftKey());
      if (!rawDraft) {
        setDraftStatus('No local draft saved yet.');
        return;
      }

      try {
        const parsed = JSON.parse(rawDraft);
        applyValuesToForm(surveyForm, parsed.values || {});
        const savedAt = parsed.updatedAt ? new Date(parsed.updatedAt).toLocaleString() : 'earlier';
        setDraftStatus('Draft restored from ' + savedAt + '.');
      } catch (error) {
        console.error('Failed to restore draft:', error);
        setDraftStatus('Saved draft could not be restored.');
      }
    }

    function clearDraft(message) {
      storage.removeItem(getDraftKey());
      setDraftStatus(message || 'Local draft cleared.');
    }

    async function persistLocalRecord(payload, settings) {
      const existing = payload.sync_uuid ? await getLocalRecord(payload.sync_uuid) : null;
      const record = buildLocalRecord(payload, {
        existing: existing || localRecord || {},
        status: settings.status,
        currentSection: settings.currentSection
      });
      await putLocalRecord(record);
      localRecord = record;
      return record;
    }

    function navigateToLocalRecord(syncUuid, section) {
      window.location.assign(buildCreateUrl(createUrl, syncUuid, section));
    }

    async function loadLocalRecordIntoForm(syncUuid) {
      const record = await getLocalRecord(syncUuid);
      if (!record) {
        setDraftStatus('This local record could not be found on the device.');
        return;
      }

      localRecord = record;
      if (syncUuidInput) {
        syncUuidInput.value = record.sync_uuid;
      }
      applyValuesToForm(surveyForm, record.payload || {});

      const sectionToOpen = requestedSection || record.current_section || currentSectionInput.value;
      if (typeof window.activateSection === 'function') {
        window.activateSection(sectionToOpen);
      } else {
        currentSectionInput.value = sectionToOpen;
      }

      setDraftStatus('Local record loaded from this device. Continue working and sync later.');
    }

    if (syncUuidInput && !syncUuidInput.value) {
      syncUuidInput.value = requestedOfflineRecord || generateSyncUuid();
    }

    surveyForm.addEventListener('input', saveDraft);
    surveyForm.addEventListener('change', saveDraft);
    surveyForm.addEventListener('submit', async function (event) {
      if (submissionInFlight) {
        event.preventDefault();
        return;
      }

      if (isEditMode && !navigator.onLine) {
        event.preventDefault();
        setDraftStatus('Editing an existing server record offline is not supported yet.');
        return;
      }

      if (isEditMode) {
        clearDraft('Draft cleared after save.');
        return;
      }

      event.preventDefault();
      submissionInFlight = true;

      const payload = serializeFormValues(surveyForm);
      if (!payload.sync_uuid) {
        payload.sync_uuid = generateSyncUuid();
        if (syncUuidInput) {
          syncUuidInput.value = payload.sync_uuid;
        }
      }

      const submitAction = submitActionInput.value || 'continue';
      const currentSection = currentSectionInput.value || 'sec-a';
      const nextSection = getNextSection(currentSection);
      const isFinalSection = nextSection === currentSection;
      const shouldStayLocal = Boolean(requestedOfflineRecord || localRecord) || !navigator.onLine;

      try {
        if (!shouldStayLocal) {
          const response = await fetch(surveyForm.action || window.location.href, {
            method: 'POST',
            body: new window.FormData(surveyForm),
            credentials: 'same-origin',
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            }
          });

          if (response.redirected) {
            clearDraft('Draft cleared after save.');
            window.location.assign(response.url);
            return;
          }

          if (response.ok) {
            const html = await response.text();
            clearDraft('Draft cleared after save.');
            document.open();
            document.write(html);
            document.close();
            return;
          }

          throw new Error('Server returned an unexpected response while saving.');
        }
      } catch (error) {
        console.warn('Falling back to local record save:', error);
      }

      try {
        const localStatus = (submitAction === 'exit' || isFinalSection) ? 'pending_sync' : 'draft';
        const targetSection = submitAction === 'continue' && !isFinalSection ? nextSection : currentSection;
        const savedRecord = await persistLocalRecord(payload, {
          status: localStatus,
          currentSection: targetSection
        });

        clearDraft('Draft cleared after local save.');

        if (submitAction === 'continue' && !isFinalSection) {
          navigateToLocalRecord(savedRecord.sync_uuid, nextSection);
          return;
        }

        storeSessionMessage('Record saved on this device. It is ready to sync when connectivity returns.', 'warning');
        window.location.assign(listUrl);
      } catch (queueError) {
        console.error('Failed to save local record:', queueError);
        setDraftStatus('This device could not store the record offline. Please reconnect and try again.');
      } finally {
        submissionInFlight = false;
      }
    });

    if (clearDraftButton) {
      clearDraftButton.addEventListener('click', function () {
        clearDraft('Local draft cleared.');
      });
    }

    if (requestedOfflineRecord) {
      loadLocalRecordIntoForm(requestedOfflineRecord).catch(function (error) {
        console.error('Failed to load local record:', error);
        setDraftStatus('This local device record could not be loaded.');
      });
      return;
    }

    restoreDraft();
  }

  initializeListSync();
  initializeSurveyForm();
})();
