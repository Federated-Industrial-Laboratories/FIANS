# Security

## Local boundary

FIANS runs as the current user. Its worker listens on a private Unix socket and
does not expose a TCP service. Model loading and speech generation use local
files. The explicit installer and model setup commands need network access to
obtain dependencies and weights.

Model hashes bind files to the distributed manifest. They do not make an untrusted
package or altered manifest safe. Install trusted application, runtime and model
sources. Keep registered model directories and profile files protected from
untrusted modification.

The worker is not a sandbox for hostile local users or arbitrary model files.
No remote-client authentication interface is provided. Exposing the internal
socket through a network service is outside the supported configuration.

## Narration data

Speech text is processed locally. Using standard input avoids placing it in the
process argument list. Rendered WAVs are written to the caller's chosen path;
the caller owns retention and access permissions for those outputs.

Temporary speech files and worker diagnostics are stored locally. Review diagnostic
logs before sharing them, since dependency failures can include local paths or
request context. Do not place secrets in narration text.

## Reporting

Report a suspected vulnerability privately to repository maintainers through an
available GitHub private reporting or organization contact channel. Do not open
a public issue containing an exploit against an unrepaired deployment or private
data. Include affected versions, reproduction steps and the observed impact.

Only the current source version is maintained. No response-time or long-term
support commitment is implied by this policy.
