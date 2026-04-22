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

  function hideAlert(alert) {
    if (!alert) {
      return;
    }

    alert.textContent = '';
    alert.className = 'alert hidden';
  }

  function storeSyncMessage(message) {
    try {
      window.sessionStorage.setItem('cpar-sync-message', message);
    } catch (error) {
      console.error('Failed to store sync message:', error);
    }
  }

  function restoreStoredSyncMessage(statusAlert) {
    if (!statusAlert) {
      return;
    }

    try {
      const message = window.sessionStorage.getItem('cpar-sync-message');
      if (!message) {
        return;
      }

      window.sessionStorage.removeItem('cpar-sync-message');
      setAlert(statusAlert, message, 'warning');
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

  function queueSubmission(entry) {
    return withSyncStore('readwrite', function (store) {
      return store.put(entry);
    });
  }

  function removeQueuedSubmission(syncUuid) {
    return withSyncStore('readwrite', function (store) {
      return store.delete(syncUuid);
    });
  }

  function getQueuedSubmissions() {
    return withSyncStore('readonly', function (store) {
      return store.getAll();
    }).then(function (entries) {
      return (entries || []).sort(function (first, second) {
        return new Date(first.createdAt).getTime() - new Date(second.createdAt).getTime();
      });
    });
  }

  function countQueuedSubmissions() {
    return getQueuedSubmissions().then(function (entries) {
      return entries.filter(function (entry) {
        return entry.status !== 'synced';
      }).length;
    });
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

  async function updatePendingSyncCount() {
    const countElement = document.querySelector('[data-pending-sync-count]');
    if (!countElement) {
      return;
    }

    try {
      const pendingCount = await countQueuedSubmissions();
      if (pendingCount === 0) {
        setText(countElement, 'All synced.');
        return;
      }

      setText(countElement, pendingCount + ' record' + (pendingCount === 1 ? '' : 's') + ' waiting to sync.');
    } catch (error) {
      console.error('Failed to read queued sync records:', error);
      setText(countElement, 'Offline queue unavailable.');
    }
  }

  async function syncQueuedRecords(syncUrl, statusAlert, options) {
    const settings = options || {};
    if (!syncUrl) {
      return { synced: 0, failed: 0 };
    }

    let queuedEntries = [];
    try {
      queuedEntries = await getQueuedSubmissions();
    } catch (error) {
      console.error('Unable to open offline queue:', error);
      if (!settings.silent) {
        setAlert(statusAlert, 'Offline queue is unavailable on this device.', 'error');
      }
      return { synced: 0, failed: 0 };
    }

    const pendingEntries = queuedEntries.filter(function (entry) {
      return entry.status !== 'synced';
    });

    if (!pendingEntries.length) {
      await updatePendingSyncCount();
      if (!settings.silent) {
        setAlert(statusAlert, 'All device-saved records are already synced.', 'success');
      }
      return { synced: 0, failed: 0 };
    }

    if (!navigator.onLine) {
      if (!settings.silent) {
        setAlert(statusAlert, 'No connection. Pending device records will sync when you are back online.', 'warning');
      }
      return { synced: 0, failed: pendingEntries.length };
    }

    const csrfToken = getCookie('csrftoken');
    let syncedCount = 0;
    let failedCount = 0;

    for (const entry of pendingEntries) {
      entry.status = 'syncing';
      entry.lastAttemptAt = new Date().toISOString();
      await queueSubmission(entry);

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

          entry.status = 'sync_failed';
          entry.error = errorMessage;
          await queueSubmission(entry);
          failedCount += 1;
          continue;
        }

        await removeQueuedSubmission(entry.sync_uuid);
        syncedCount += 1;
      } catch (error) {
        entry.status = 'sync_failed';
        entry.error = error.message || 'Network error while syncing.';
        await queueSubmission(entry);
        failedCount += 1;
        break;
      }
    }

    await updatePendingSyncCount();

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

    updatePendingSyncCount();
    restoreStoredSyncMessage(statusAlert);

    if (!syncButton) {
      return;
    }

    syncButton.addEventListener('click', function () {
      syncQueuedRecords(syncUrl, statusAlert, { silent: false });
    });

    window.addEventListener('online', function () {
      syncQueuedRecords(syncUrl, statusAlert, { silent: true }).then(function (result) {
        if (result.synced > 0) {
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

    if (!surveyForm) {
      return;
    }

    const draftKey = surveyForm.dataset.draftKey;
    const isEditMode = surveyForm.dataset.recordMode === 'edit';
    const listUrl = surveyForm.dataset.listUrl || '/surveys/';
    const syncUuidInput = surveyForm.querySelector('#sync-uuid-input');
    const storage = window.localStorage;

    function setDraftStatus(message) {
      setText(draftStatus, message);
    }

    function saveDraft() {
      const payload = serializeFormValues(surveyForm);

      storage.setItem(draftKey, JSON.stringify({
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

      const rawDraft = storage.getItem(draftKey);
      if (!rawDraft) {
        setDraftStatus('No local draft saved yet.');
        return;
      }

      try {
        const parsed = JSON.parse(rawDraft);
        Object.entries(parsed.values || {}).forEach(function (entry) {
          const name = entry[0];
          const value = entry[1];
          const field = surveyForm.elements.namedItem(name);

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

          field.value = value;
        });

        const savedAt = parsed.updatedAt ? new Date(parsed.updatedAt).toLocaleString() : 'earlier';
        setDraftStatus('Draft restored from ' + savedAt + '.');
      } catch (error) {
        console.error('Failed to restore draft:', error);
        setDraftStatus('Saved draft could not be restored.');
      }
    }

    function clearDraft(message) {
      storage.removeItem(draftKey);
      setDraftStatus(message || 'Local draft cleared.');
    }

    if (syncUuidInput && !syncUuidInput.value) {
      syncUuidInput.value = generateSyncUuid();
    }

    surveyForm.addEventListener('input', saveDraft);
    surveyForm.addEventListener('change', saveDraft);
    surveyForm.addEventListener('submit', function (event) {
      if (navigator.onLine) {
        clearDraft('Draft cleared after save.');
        return;
      }

      event.preventDefault();

      const payload = serializeFormValues(surveyForm);
      if (!payload.sync_uuid) {
        payload.sync_uuid = generateSyncUuid();
        if (syncUuidInput) {
          syncUuidInput.value = payload.sync_uuid;
        }
      }

      queueSubmission({
        sync_uuid: payload.sync_uuid,
        payload: payload,
        status: 'pending_sync',
        createdAt: new Date().toISOString(),
        lastAttemptAt: null,
        error: ''
      }).then(function () {
        clearDraft('Draft cleared after local save.');
        storeSyncMessage('Record saved on this device. It will sync to the server when connectivity returns.');
        window.location.assign(listUrl);
      }).catch(function (error) {
        console.error('Failed to queue offline record:', error);
        setDraftStatus('This device could not store the record offline. Please reconnect and try again.');
      });
    });

    if (clearDraftButton) {
      clearDraftButton.addEventListener('click', function () {
        clearDraft('Local draft cleared.');
      });
    }

    restoreDraft();
  }

  initializeListSync();
  initializeSurveyForm();
})();
