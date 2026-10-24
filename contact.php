<?php
declare(strict_types=1);

// Requires PHP 8.1+ and an outgoing mail transport configured by the hosting provider.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('X-Robots-Tag: noindex, nofollow');

function respond(int $status, array $body): never {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'] ?? '';
if (!in_array($method, ['GET', 'POST'], true)) {
    header('Allow: GET, POST');
    respond(405, ['error' => 'Ugyldig forespørsel.']);
}
if ((int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 24000) {
    respond(413, ['error' => 'Meldingen er for stor.']);
}
session_set_cookie_params([
    'httponly' => true,
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    'samesite' => 'Strict',
]);
if (!session_start()) {
    respond(503, ['error' => 'Skjemaet er midlertidig utilgjengelig. Ring +47 900 12 461 eller send e-post til post@norrengjoring.no.']);
}
if ($method === 'GET') {
    if (!isset($_SESSION['contact_token'], $_SESSION['contact_token_time']) || time() - $_SESSION['contact_token_time'] > 1800) {
        $_SESSION['contact_token'] = bin2hex(random_bytes(32));
        $_SESSION['contact_token_time'] = time();
    }
    respond(200, ['token' => $_SESSION['contact_token']]);
}

$token = $_POST['token'] ?? null;
if (!is_string($token) || !isset($_SESSION['contact_token'], $_SESSION['contact_token_time']) ||
    time() - $_SESSION['contact_token_time'] > 1800 || !hash_equals($_SESSION['contact_token'], $token)) {
    respond(403, ['error' => 'Skjemaøkten er utløpt. Prøv å sende på nytt.']);
}
$fields = [];
foreach (['navn' => 200, 'epost' => 254, 'tlf' => 60, 'emne' => 240, 'melding' => 10000, 'website' => 200] as $name => $limit) {
    $value = $_POST[$name] ?? '';
    if (!is_string($value) || strlen($value) > $limit) {
        respond(422, ['error' => 'Et felt er for langt eller ugyldig. Kontroller opplysningene.']);
    }
    $fields[$name] = trim($value);
}
if ($fields['website'] !== '') {
    respond(422, ['error' => 'Meldingen kunne ikke sendes. Kontakt oss på telefon eller e-post.']);
}
if ($fields['navn'] === '' || $fields['melding'] === '' || !filter_var($fields['epost'], FILTER_VALIDATE_EMAIL) ||
    preg_match('/[\r\n\x00]/', $fields['navn'] . $fields['epost'] . $fields['emne'])) {
    respond(422, ['error' => 'Oppgi navn, gyldig e-postadresse og en melding.']);
}
$attempts = array_values(array_filter($_SESSION['contact_attempts'] ?? [], fn ($at) => is_int($at) && $at > time() - 600));
if (count($attempts) >= 5 || time() - ($_SESSION['contact_sent_at'] ?? 0) < 30) {
    header('Retry-After: 60');
    respond(429, ['error' => 'Du har sendt flere forespørsler. Vent litt før du prøver igjen.']);
}
$attempts[] = time();
$_SESSION['contact_attempts'] = $attempts;

$recipient = 'post@norrengjoring.no';
$subject = 'Nettside: ' . ($fields['emne'] ?: 'Ny henvendelse');
$subject = '=?UTF-8?B?' . base64_encode($subject) . '?=';
$body = "Henvendelse fra nettsiden\n\nNavn: {$fields['navn']}\nE-post: {$fields['epost']}\nTelefon: {$fields['tlf']}\n\n{$fields['melding']}\n";
$headers = [
    'From' => 'Nor Rengjoring <no-reply@norrengjoring.no>',
    'Reply-To' => $fields['epost'],
    'MIME-Version' => '1.0',
    'Content-Type' => 'text/plain; charset=UTF-8',
    'Content-Transfer-Encoding' => '8bit',
];
// Explicit server-side test mode never sends email and is clearly identified to the browser.
$testMode = getenv('NOR_CONTACT_TEST_MODE') === '1';
$sent = $testMode || @mail($recipient, $subject, $body, $headers);
if (!$sent) {
    respond(503, ['error' => 'Meldingen ble ikke sendt. Prøv igjen senere, ring +47 900 12 461 eller send e-post til post@norrengjoring.no.']);
}
$_SESSION['contact_sent_at'] = time();
unset($_SESSION['contact_token'], $_SESSION['contact_token_time']);
respond(200, [
    'ok' => true,
    'test_mode' => $testMode,
    'message' => $testMode
        ? 'Testmodus: Skjemaet fungerer, men ingen e-post er sendt.'
        : 'Takk! Meldingen er sendt til vår e-posttjeneste. Vi tar kontakt så snart som mulig.',
]);
