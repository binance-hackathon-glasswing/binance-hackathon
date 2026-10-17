"""IDEA-081 prospective acceptance: per-stage Markdown prompts for the routed assessor.

SP1 composed prompt on the wire; SP2 recorded hashes and keys; SP3 refusals before transport;
SP4 v1 unchanged; SP5 router identity covers addenda; SP7 addenda are release files.
Synthetic HTTP only; no keys or network.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from larp.intelligence.common import IntelligenceError
from larp.intelligence.routing import STAGE_PROMPT_DIR, build_routed_assessor, validate_routing_spec
from larp.runtime.preflight import release_files
from tests.intelligence import test_aiand_routing as base  # module import: pytest must not collect Routing twice

AIAND_KEY, OPENAI_KEY, ROOT = base.AIAND_KEY, base.OPENAI_KEY, base.ROOT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def addendum(name):
    return (STAGE_PROMPT_DIR / name).read_text(encoding='utf-8')


def v1(spec):
    spec = deepcopy(spec)
    spec['schema'] = 'AIandRouting.v1'
    spec.pop('openai_prompt')
    for entry in [spec['routine'], *spec['external_reviewers']]:
        entry.pop('prompt')
    return spec


class StagePrompts(unittest.TestCase):
    setUp, openai, build, run_assessment = base.Routing.setUp, base.Routing.openai, base.Routing.build, base.Routing.run_assessment

    def aiand(self, url, headers, raw, timeout):
        self.bodies.append(('aiand', json.loads(raw)))
        return base.Routing.aiand(self, url, headers, raw, timeout)

    def openai_recorded(self, url, headers, raw, timeout):
        self.bodies.append(('openai', json.loads(raw)))
        return self.openai(url, headers, raw, timeout)

    def router(self, spec=None, prompt_dir=STAGE_PROMPT_DIR, key=True):
        self.bodies = []
        secrets = {'LARP_AIAND_API_KEY': AIAND_KEY}
        if key:
            secrets['LARP_MODEL_API_KEY'] = OPENAI_KEY
        return build_routed_assessor(spec or self.s, registry=self.w.registry, reader=self.w.reader,
                                     config=self.w.config, clock_ms=self.w.clock, artifacts=self.w.artifacts,
                                     secrets=secrets, budget_root=self.root, prompt_dir=prompt_dir,
                                     transports={'aiand': self.aiand, 'openai': self.openai_recorded})

    def composed(self, name):
        return self.w.config.prompt_text.rstrip('\n') + '\n\n' + addendum(name)

    def stage_results(self, value):
        return {s['stage']: json.loads(self.w.artifacts.get(s['result_artifact'])) for s in value['routing']['stages']}

    def test_example_spec_is_v2_and_pins_the_shipped_addenda(self):
        self.assertEqual(self.s['schema'], 'AIandRouting.v2')
        self.assertEqual(self.s['routine']['prompt']['name'], 'routine.md')
        for entry in [*self.s['external_reviewers'], self.s['openai_prompt']]:
            prompt = entry.get('prompt', entry)
            self.assertEqual(prompt['name'], 'review.md')
            self.assertEqual(prompt['sha256'], sha((STAGE_PROMPT_DIR / 'review.md').read_bytes()))

    def test_sp1_each_stage_sends_core_prompt_plus_its_addendum(self):
        router = self.router()
        self.assertFalse(self.bodies)  # construction makes no request
        self.run_assessment(router)
        self.assertTrue(any(kind == 'openai' for kind, _ in self.bodies))
        for kind, body in self.bodies:
            if kind == 'aiand':
                expected = 'routine.md' if body['reasoning_effort'] == 'low' else 'review.md'
                self.assertEqual(body['messages'][0], dict(role='system', content=self.composed(expected)))
            else:
                self.assertEqual(body['instructions'], self.composed('review.md'))
        self.assertTrue(self.composed('routine.md').startswith(self.w.config.prompt_text))

    def test_sp1_external_only_review_uses_review_prompt(self):
        self.run_assessment(self.router(key=False))
        high = [b for k, b in self.bodies if k == 'aiand' and b['reasoning_effort'] == 'high']
        self.assertTrue(high)
        for body in high:
            self.assertEqual(body['messages'][0]['content'], self.composed('review.md'))

    def test_sp2_stage_results_record_the_composed_prompt_hash(self):
        _, value = self.run_assessment(self.router())
        stages = self.stage_results(value)
        routine_hash = sha(self.composed('routine.md').encode())
        review_hash = sha(self.composed('review.md').encode())
        self.assertNotEqual(routine_hash, review_hash)
        self.assertEqual(stages['routine']['prompt_hash'], routine_hash)
        self.assertIn('openai-review', stages)
        for name, result in stages.items():
            if name != 'routine':
                self.assertEqual(result['prompt_hash'], review_hash, name)
            for step in result['model_io']['steps']:
                self.assertEqual(step['request']['prompt_sha256'], result['prompt_hash'])
        self.assertNotIn(self.w.config.prompt_sha256, {r['prompt_hash'] for r in stages.values()})

    def test_sp2_assessment_key_changes_with_the_addendum(self):
        _, value = self.run_assessment(self.router())
        staged = self.stage_results(value)['routine']['assessment_key']
        self.setUp()
        _, value = self.run_assessment(self.router(v1(self.s)))
        self.assertNotEqual(staged, self.stage_results(value)['routine']['assessment_key'])

    def test_sp3_bad_prompt_pins_are_refused_before_any_request(self):
        def mutate(path, value):
            def apply(spec):
                node = spec
                for key in path[:-1]:
                    node = node[key]
                if value is KeyError:
                    node.pop(path[-1])
                else:
                    node[path[-1]] = value
            return apply
        cases = {
            'hash mismatch': mutate(['routine', 'prompt', 'sha256'], '0' * 64),
            'missing openai prompt': mutate(['openai_prompt'], KeyError),
            'missing reviewer prompt': mutate(['external_reviewers', 0, 'prompt'], KeyError),
            'extra key': mutate(['routine', 'prompt', 'path'], '/etc/passwd'),
            'separator': mutate(['routine', 'prompt', 'name'], 'routing/routine.md'),
            'traversal': mutate(['routine', 'prompt', 'name'], '../assessor.v2.txt'),
            'not markdown': mutate(['routine', 'prompt', 'name'], 'routine.txt'),
            'hidden': mutate(['routine', 'prompt', 'name'], '.routine.md'),
            'missing file': mutate(['routine', 'prompt', 'name'], 'absent.md'),
            'bad hash form': mutate(['openai_prompt', 'sha256'], 'ABC'),
            'unknown schema': mutate(['schema'], 'AIandRouting.v3'),
        }
        for name, apply in cases.items():
            spec = deepcopy(self.s)
            apply(spec)
            with self.subTest(name), self.assertRaises(IntelligenceError):
                self.router(spec)
            self.assertFalse(self.bodies)
            self.assertFalse(self.calls)
        spec = v1(self.s)
        spec['routine']['prompt'] = deepcopy(self.s['routine']['prompt'])
        with self.assertRaises(IntelligenceError):
            self.router(spec)

    def test_sp4_v1_spec_sends_and_records_the_core_prompt(self):
        _, value = self.run_assessment(self.router(v1(self.s)))
        self.assertTrue(self.bodies)
        for kind, body in self.bodies:
            sent = body['messages'][0]['content'] if kind == 'aiand' else body['instructions']
            self.assertEqual(sent, self.w.config.prompt_text)
        for result in self.stage_results(value).values():
            self.assertEqual(result['prompt_hash'], self.w.config.prompt_sha256)

    def test_sp5_router_identity_covers_every_addendum(self):
        base = self.router().model.identity.model_hash
        self.assertNotEqual(base, self.router(v1(self.s)).model.identity.model_hash)
        with tempfile.TemporaryDirectory() as tmp:
            prompts = Path(tmp)
            for name in ('routine.md', 'review.md'):
                shutil.copy(STAGE_PROMPT_DIR / name, prompts / name)
            (prompts / 'review-alt.md').write_text(addendum('review.md') + '\nExtra line.\n', encoding='utf-8')
            alt = dict(name='review-alt.md', sha256=sha((prompts / 'review-alt.md').read_bytes()))
            for where in ('openai', 'reviewer'):
                spec = deepcopy(self.s)
                if where == 'openai':
                    spec['openai_prompt'] = alt
                else:
                    spec['external_reviewers'][0]['prompt'] = alt
                with self.subTest(where):
                    self.assertNotEqual(base, self.router(spec, prompts).model.identity.model_hash)

    def test_sp8_shared_validator_accepts_v2_and_refuses_bad_prompt_pins(self):
        validate_routing_spec(self.s)
        validate_routing_spec(v1(self.s))
        bad = {}
        bad['v2 without openai prompt'] = deepcopy(self.s); bad['v2 without openai prompt'].pop('openai_prompt')
        bad['v2 reviewer without prompt'] = deepcopy(self.s); bad['v2 reviewer without prompt']['external_reviewers'][1].pop('prompt')
        bad['v1 with prompt'] = v1(self.s); bad['v1 with prompt']['routine']['prompt'] = deepcopy(self.s['routine']['prompt'])
        bad['v1 with openai prompt'] = v1(self.s); bad['v1 with openai prompt']['openai_prompt'] = deepcopy(self.s['openai_prompt'])
        bad['hash mismatch'] = deepcopy(self.s); bad['hash mismatch']['openai_prompt']['sha256'] = '1' * 64
        bad['missing file'] = deepcopy(self.s); bad['missing file']['routine']['prompt']['name'] = 'secret-name-xyz.md'
        for name, spec in bad.items():
            with self.subTest(name), self.assertRaises(IntelligenceError) as caught:
                validate_routing_spec(spec)
            self.assertNotIn('secret-name-xyz', str(caught.exception))

    def test_sp7_addenda_are_release_files_and_no_other_config_markdown_is(self):
        files = release_files(ROOT)
        for name in ('routine.md', 'review.md'):
            self.assertIn(f'config/intelligence/prompts/routing/{name}', files)
        markdown = {f for f in files if f.startswith('config/') and f.endswith('.md')}
        self.assertTrue(all(f.startswith('config/intelligence/prompts/') for f in markdown), markdown)

    def test_sp9_invalid_text_or_release_escape_refuses_before_budget_construction(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompts = root / 'prompts'
            prompts.mkdir()
            for name in ('routine.md', 'review.md'):
                shutil.copy(STAGE_PROMPT_DIR / name, prompts / name)
            outside = root / 'outside.md'
            outside.write_bytes(b'Valid text outside the release prompt directory.\n')
            for defect in ('utf8', 'empty', 'oversized', 'symlink', 'backslash', 'dotdot', 'nul'):
                bad = prompts / 'bad.md'
                if bad.exists() or bad.is_symlink(): bad.unlink()
                raw = {'utf8': b'\xff', 'empty': b' \n', 'oversized': b'x' * (16 * 1024 + 1)}.get(
                    defect, b'Valid text.\n')
                name = 'bad.md'
                if defect == 'symlink':
                    bad.symlink_to(outside)
                    raw = outside.read_bytes()
                elif defect in ('backslash', 'dotdot'):
                    name = 'private\\prompt.md' if defect == 'backslash' else 'private..md'
                    (prompts / name).write_bytes(raw)
                elif defect == 'nul':
                    name = 'private\x00.md'
                else:
                    bad.write_bytes(raw)
                spec = deepcopy(self.s)
                spec['openai_prompt'] = dict(name=name, sha256=sha(raw))
                with self.subTest(defect=defect), patch('larp.intelligence.routing.ModelBudget',
                        side_effect=AssertionError('Invalid prompt reached budget construction')):
                    with self.assertRaises(IntelligenceError):
                        validate_routing_spec(spec, prompt_dir=prompts)
                    with self.assertRaises(IntelligenceError) as caught:
                        self.router(spec, prompt_dir=prompts)
                    self.assertNotIn('private', str(caught.exception))
                    self.assertFalse(self.calls)


if __name__ == '__main__':
    unittest.main()
