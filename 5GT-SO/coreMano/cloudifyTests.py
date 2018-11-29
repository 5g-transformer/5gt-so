import unittest
from cloudifyWrapper import CloudifyWrapper
from coreManoWrapper import createWrapper
class TestCloudifyWrapper(unittest.TestCase):

    # def test_create_nsi(self):
    #     cw = CloudifyWrapper.get_instance()
    #     nsi_id = cw.create_ns()
    #     self.assertTrue(isinstance(nsi_id, str))

    
    # def test_instantiate_nsi(self):
    #     cw = CloudifyWrapper.get_instance()
    #     nsi_id = cw.create_ns()
    #     operation_id = cw.instantiate_ns(nsi_id)
    #     self.assertTrue(isinstance(operation_id, str))

    
    # def test_get_execution(self):
    #     cw = CloudifyWrapper.get_instance()
    #     execution = cw.get_execution("f2778336-ec5a-4bfa-a2a0-b59991455d5d") 
    #     self.assertTrue(isinstance(execution["deployment_id"], str))


    # def test_terminate_nsi(self):
    #     import os
    #     print(os.getcwd())
    #     cw = CloudifyWrapper.get_instance("name","192.168.137.39")
    #     nsi_id = cw.create_ns()
    #     operation_id = cw.instantiate_ns(nsi_id)
    #     status = cw.query_operation_status(operation_id)
    #     self.assertTrue(isinstance(status["id"], str))
    #     cw.terminate_ns(nsi_id)
    #     self.assertTrue(isinstance("", str))


    def test_nbi(self):
                
        coreMano = createWrapper()
        deployed_vnfs_info = coreMano.create_ns(None, None)


if __name__ == '__main__':
    unittest.main()