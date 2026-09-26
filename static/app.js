// Small progressive-enhancement behaviors: file dropzone + password visibility toggle.
// Both degrade gracefully — the underlying <input> elements work fine without this file.
(function () {
    function initDropzones() {
        document.querySelectorAll('[data-dropzone]').forEach(function (zone) {
            var input = zone.querySelector('input[type="file"]');
            var filledText = zone.querySelector('.dropzone-text-filled');
            var clearBtn = zone.querySelector('.dropzone-clear');
            if (!input) return;

            function showFile(name) {
                zone.classList.add('dropzone-filled');
                zone.classList.remove('dropzone-error');
                if (filledText) filledText.textContent = name;
            }

            function reset() {
                zone.classList.remove('dropzone-filled');
                if (filledText) filledText.textContent = '';
                input.value = '';
            }

            input.addEventListener('change', function () {
                if (input.files && input.files.length) {
                    showFile(input.files[0].name);
                } else {
                    reset();
                }
            });

            ['dragenter', 'dragover'].forEach(function (evt) {
                zone.addEventListener(evt, function (e) {
                    e.preventDefault();
                    zone.classList.add('dropzone-drag');
                });
            });
            ['dragleave', 'drop'].forEach(function (evt) {
                zone.addEventListener(evt, function (e) {
                    e.preventDefault();
                    zone.classList.remove('dropzone-drag');
                });
            });

            if (clearBtn) {
                clearBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    reset();
                });
            }

            // Restore filename if the page re-rendered with a validation error
            // and the browser preserved the file input's value.
            if (input.files && input.files.length) showFile(input.files[0].name);
        });
    }

    function initPasswordToggles() {
        document.querySelectorAll('.password-field').forEach(function (wrap) {
            var input = wrap.querySelector('input');
            var btn = wrap.querySelector('.password-toggle');
            if (!input || !btn) return;
            var eye = btn.querySelector('.icon-eye');
            var eyeOff = btn.querySelector('.icon-eye-off');

            btn.addEventListener('click', function () {
                var showing = input.type === 'text';
                input.type = showing ? 'password' : 'text';
                btn.setAttribute('aria-pressed', String(!showing));
                btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
                if (eye) eye.style.display = showing ? 'block' : 'none';
                if (eyeOff) eyeOff.style.display = showing ? 'none' : 'block';
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initDropzones();
        initPasswordToggles();
    });
})();