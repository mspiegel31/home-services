import gc
import unittest

import torch

from vllm.model_executor.layers.quantization.csf_ram_offload import allocate_packed_weights
from vllm.model_executor.offloader.base import get_offloader, set_offloader
from vllm.model_executor.offloader.uva import UVAOffloader


class CsfRamOffloadTest(unittest.TestCase):
    def setUp(self):
        self.previous = get_offloader()
        torch.cuda.synchronize()
        gc.collect()

    def tearDown(self):
        set_offloader(self.previous)

    def test_budget_stops_after_whole_tensor_and_gpu_can_read_host_bytes(self):
        offloader = UVAOffloader(1023, {"experts"})
        set_offloader(offloader)
        before = torch.cuda.memory_allocated()
        weights = allocate_packed_weights(((1024,), (512,)), "cuda", "model.layers.0.mlp.experts")
        torch.cuda.synchronize()
        self.assertEqual(offloader.cpu_offload_bytes, 1024)
        self.assertEqual(torch.cuda.memory_allocated() - before, 512)
        weights[0].fill_(73)
        torch.cuda.synchronize()
        self.assertTrue(torch.equal(weights[0].cpu(), torch.full((1024,), 73, dtype=torch.uint8)))

    def test_segment_matching_does_not_offload_attention_or_near_matches(self):
        for layer in ("model.layers.0.attention", "model.layers.0.mlp.expert"):
            with self.subTest(layer=layer):
                offloader = UVAOffloader(4096, {"experts"})
                set_offloader(offloader)
                before = torch.cuda.memory_allocated()
                weights = allocate_packed_weights(((1024,), (512,)), "cuda", layer)
                torch.cuda.synchronize()
                self.assertEqual(offloader.cpu_offload_bytes, 0)
                self.assertEqual(torch.cuda.memory_allocated() - before, 1536)
                del weights
                gc.collect()

    def test_empty_target_set_offloads_both_packed_projections(self):
        offloader = UVAOffloader(1536)
        set_offloader(offloader)
        before = torch.cuda.memory_allocated()
        weights = allocate_packed_weights(((1024,), (512,)), "cuda", "model.layers.0.mlp.experts")
        torch.cuda.synchronize()
        self.assertEqual(offloader.cpu_offload_bytes, 1536)
        self.assertEqual(torch.cuda.memory_allocated(), before)
        self.assertEqual([int(weight.sum()) for weight in weights], [0, 0])


if __name__ == "__main__":
    unittest.main()
