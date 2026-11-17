"""Positive and adversarial tests for Scalability & Real-Time Audio Safety rules (SCA-001..SCA-004).

@category: unit
@category: adversarial
"""

from __future__ import annotations

import unittest

from tools.xlp_gate.tests.helpers import (
    check_rule,
    create_compliant_workspace,
    read_json,
    rule_ids_in,
    write_json,
)


class TestScalabilityAndRTSafetyRules(unittest.TestCase):
    def test_sca_001_positive_allows_prepare_preallocation_and_comments(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                """
#pragma once
#include <vector>

namespace xlp {
class SafeFilter {
public:
    // Note: malloc() or std::mutex in comments must never false-positive.
    void prepareToPlay(double sample_rate, int max_block) {
        buffer_.resize(static_cast<size_t>(max_block));
        scratch_.reserve(1024);
    }

    // XLP_NON_RT_BEGIN
    void rebuild_tables() {
        table_.push_back(1.0f);
    }
    // XLP_NON_RT_END

    float process_sample(float x) noexcept {
        const char* tag = "malloc(10) std::mutex";
        (void)tag;
        return x * 0.5f;
    }

private:
    std::vector<float> buffer_;
    std::vector<float> scratch_;
    std::vector<float> table_;
};
}
""",
                encoding="utf-8",
            )
            rep = check_rule(root, "SCA-001")
            self.assertTrue(rep.passed, rep.findings)

    def test_sca_001_adversarial_catches_alloc_lock_io_throw_and_push_back(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            (root / "plugins" / "xlp_filter_one" / "dsp" / "processor.hpp").write_text(
                """
#pragma once
#include <mutex>
#include <vector>
#include <cstdio>

namespace xlp {
class UnsafeFilter {
public:
    void process(float* out, int n) {
        std::lock_guard<std::mutex> guard(mtx_);
        auto* raw = malloc(64);
        int* p = new int[4];
        std::printf("glitch %d\\n", n);
        history_.push_back(out[0]);
        if (n < 0) { throw std::runtime_error("bad"); }
        free(raw);
        delete[] p;
    }
private:
    std::mutex mtx_;
    std::vector<float> history_;
};
}
""",
                encoding="utf-8",
            )
            rep = check_rule(root, "SCA-001")
            self.assertIn("SCA-001", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 6)

    def test_sca_001_adversarial_catches_rust_rt_violations(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            (root / "plugins" / "xlp_filter_one" / "dsp" / "engine.rs").write_text(
                """
pub fn process_block(samples: &mut [f32], log: &mut Vec<f32>) {
    println!("debug");
    let _f = File::open("bad.txt");
    thread::sleep(std::time::Duration::from_millis(1));
    log.push(samples[0]);
}
""",
                encoding="utf-8",
            )
            rep = check_rule(root, "SCA-001")
            self.assertIn("SCA-001", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 4)

    def test_sca_002_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            rep = check_rule(root, "SCA-002")
            self.assertTrue(rep.passed, rep.findings)

    def test_sca_002_adversarial_mutex_comm_and_no_denormal_protection(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["realtime_contract"]["denormal_protection"] = False
            data["realtime_contract"]["thread_communication"] = "mutex"
            data["realtime_contract"]["supported_sample_rates"] = [44100]
            write_json(mpath, data)
            rep = check_rule(root, "SCA-002")
            self.assertIn("SCA-002", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 3)

    def test_sca_003_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            rep = check_rule(root, "SCA-003")
            self.assertTrue(rep.passed, rep.findings)

    def test_sca_003_adversarial_missing_or_unrealistic_budget(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True, with_module=True)
        with tmp:
            pmanifest = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            pdata = read_json(pmanifest)
            pdata["performance_budget"]["max_cpu_percent_single_core_48k_64buf"] = 95.0
            write_json(pmanifest, pdata)

            mmanifest = root / "core" / "dsp_core" / "module.manifest.json"
            mdata = read_json(mmanifest)
            del mdata["performance_budget"]
            write_json(mmanifest, mdata)

            rep = check_rule(root, "SCA-003")
            self.assertIn("SCA-003", rule_ids_in(rep))
            self.assertGreaterEqual(len(rep.findings), 2)

    def test_sca_004_positive(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            rep = check_rule(root, "SCA-004")
            self.assertTrue(rep.passed, rep.findings)

    def test_sca_004_adversarial_missing_vst3_format(self) -> None:
        tmp, root = create_compliant_workspace(with_plugin=True)
        with tmp:
            mpath = root / "plugins" / "xlp_filter_one" / "plugin.manifest.json"
            data = read_json(mpath)
            data["formats"] = ["standalone"]
            write_json(mpath, data)
            rep = check_rule(root, "SCA-004")
            self.assertIn("SCA-004", rule_ids_in(rep))


if __name__ == "__main__":
    unittest.main()
