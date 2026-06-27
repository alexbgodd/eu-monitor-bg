document.getElementById('register-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const btn = document.getElementById('submit-btn');
    const msg = document.getElementById('message');

    const name     = document.getElementById('name').value.trim();
    const email    = document.getElementById('email').value.trim();
    const org_type = document.getElementById('org_type').value;
    const interests = Array.from(
        document.querySelectorAll('.checkboxes input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    if (!name || !email) {
        showMessage('Моля попълни Имe и Имейл.', 'error');
        return;
    }

    if (interests.length === 0) {
        showMessage('Избери поне един интерес.', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Регистриране...';

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, org_type, interests })
        });

        const data = await res.json();

        if (res.ok) {
            showMessage('✓ ' + data.message, 'success');
            document.getElementById('register-form').reset();
        } else {
            showMessage(data.error || 'Грешка. Опитай отново.', 'error');
        }
    } catch (err) {
        showMessage('Грешка при свързване. Опитай отново.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Регистрирай се безплатно';
    }
});

function showMessage(text, type) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = 'message ' + type;
}
