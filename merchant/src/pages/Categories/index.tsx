import { Tabs } from 'antd';
import MajorCategories from './MajorCategories';
import MinorCategories from './MinorCategories';

export default function Categories() {
  return (
    <Tabs
      defaultActiveKey="major"
      items={[
        {
          label: '空间管理',
          key: 'major',
          children: <MajorCategories />,
        },
        {
          label: '品类管理',
          key: 'minor',
          children: <MinorCategories />,
        },
      ]}
    />
  );
}
