import { Modal, Spin } from 'antd';

type ExportLoadingModalProps = {
  open: boolean;
  text?: string;
};

export default function ExportLoadingModal({ open, text = '正在导出' }: ExportLoadingModalProps) {
  return (
    <Modal
      open={open}
      footer={null}
      closable={false}
      maskClosable={false}
      keyboard={false}
      centered
      width={240}
    >
      <div style={{ textAlign: 'center', padding: '24px 0' }}>
        <Spin />
        <div style={{ marginTop: 12 }}>{text}</div>
      </div>
    </Modal>
  );
}
