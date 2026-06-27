const SUPABASE_URL = 'https://jrbmhftixkwcgyjuijji.supabase.co';
const SUPABASE_KEY = 'sb_publishable_p2RG_e2n7Dm-D6cnzCGrbg_oZAibpIY';

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
        const res = await fetch(`${SUPABASE_URL}/rest/v1/registrations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'apikey': SUPABASE_KEY,
                'Authorization': `Bearer ${SUPABASE_KEY}`
            },
            body: JSON.stringify({
                name,
                email,
                org_type,
                interests: interests.join(', ')
            })
        });

        if (res.ok || res.status === 201) {
            showMessage('✓ Регистрацията е успешна! Ще получаваш имейл alerts.', 'success');
            document.getElementById('register-form').reset();
        } else {
            const data = await res.json();
            showMessage(data.message || 'Грешка. Опитай отново.', 'error');
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
