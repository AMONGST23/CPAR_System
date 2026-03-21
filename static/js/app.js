(function () {
  const offlineBanner = document.getElementById('offline-banner');

  function updateOnlineState() {
    if (!offlineBanner) {
      return;
    }
    offlineBanner.classList.toggle('hidden', navigator.onLine);
  }

  window.addEventListener('online', updateOnlineState);
  window.addEventListener('offline', updateOnlineState);
  updateOnlineState();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/static/js/service-worker.js').catch(function (error) {
        console.error('Service worker registration failed:', error);
      });
    });
  }

  const surveyForm = document.querySelector('[data-draft-key]');
  const draftStatus = document.querySelector('[data-draft-status]');
  const clearDraftButton = document.querySelector('[data-clear-draft]');

  if (!surveyForm) {
    return;
  }

  const draftKey = surveyForm.dataset.draftKey;
  const isEditMode = surveyForm.dataset.recordMode === 'edit';
  const storage = window.localStorage;
  const excludedFields = new Set(['csrfmiddlewaretoken']);

  function setDraftStatus(message) {
    if (draftStatus) {
      draftStatus.textContent = message;
    }
  }

  function saveDraft() {
    const payload = {};
    const elements = surveyForm.querySelectorAll('input, select, textarea');

    elements.forEach(function (field) {
      if (!field.name || field.disabled || excludedFields.has(field.name)) {
        return;
      }

      if (field.type === 'checkbox' || field.type === 'radio') {
        payload[field.name] = field.checked;
        return;
      }

      payload[field.name] = field.value;
    });

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
      Object.entries(parsed.values || {}).forEach(function ([name, value]) {
        const field = surveyForm.elements.namedItem(name);
        if (!field || excludedFields.has(name) || field instanceof RadioNodeList) {
          return;
        }

        if (field.type === 'checkbox' || field.type === 'radio') {
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

  surveyForm.addEventListener('input', saveDraft);
  surveyForm.addEventListener('change', saveDraft);
  surveyForm.addEventListener('submit', function () {
    clearDraft('Draft cleared after save.');
  });

  if (clearDraftButton) {
    clearDraftButton.addEventListener('click', function () {
      clearDraft('Local draft cleared.');
    });
  }

  restoreDraft();
})();
