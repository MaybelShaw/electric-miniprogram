import { Tabs } from 'antd';
import MajorCategories from './MajorCategories';
import MinorCategories from './MinorCategories';
import ItemCategories from './ItemCategories';

export default function Categories() {
  return (
    <Tabs
      defaultActiveKey="major"
      items={[
        {
          label: '品类管理',
          key: 'major',
          children: <MajorCategories />,
        },
        {
          label: '子品类管理',
          key: 'minor',
          children: <MinorCategories />,
        },
        {
          label: '品项管理',
          key: 'item',
          children: <ItemCategories />,
        },
      ]}
    />
  );
}
