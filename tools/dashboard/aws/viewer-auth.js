// IDEA-092: CloudFront Function (cloudfront-js-2.0, viewer request). The page is served only to a request whose HTTP
// basic-auth header hashes (SHA-256, hex, of the base64 "user:password" part) to the value an operator put in the
// distribution's KeyValueStore under `basic-auth-sha256`. Neither the password nor its hash is in the repository or the
// Terraform state. A missing key or any lookup error refuses the request.
import cf from 'cloudfront';
import crypto from 'crypto';

const kvs = cf.kvs();

function refuse() {
  return {
    statusCode: 401,
    statusDescription: 'Unauthorized',
    headers: { 'www-authenticate': { value: 'Basic realm="LARP dashboard", charset="UTF-8"' } }
  };
}

async function handler(event) {
  const request = event.request;
  const header = request.headers.authorization && request.headers.authorization.value;
  if (typeof header !== 'string' || header.indexOf('Basic ') !== 0) return refuse();
  let expected;
  try {
    expected = await kvs.get('basic-auth-sha256');
  } catch (e) {
    return refuse();
  }
  const actual = crypto.createHash('sha256').update(header.slice(6)).digest('hex');
  return typeof expected === 'string' && expected.length === 64 && actual === expected ? request : refuse();
}
