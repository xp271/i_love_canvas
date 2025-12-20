"""
网页元素点击器（主程序）
根据 HTML 文件中的行号定位并点击浏览器中的对应元素
"""
import asyncio
import argparse
from element_clicker import ElementClicker


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='网页元素点击器 - 根据 HTML 文件行号点击浏览器中的元素',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python clicker.py output/file.html 484
  python clicker.py output/file.html 484 --url https://sit.instructure.com/
        """
    )
    parser.add_argument('html_file', type=str, help='HTML 文件路径')
    parser.add_argument('line_number', type=int, help='行号（从 1 开始）')
    parser.add_argument('--url', type=str, default=None, 
                       help='目标页面 URL（可选，默认使用当前页面）')
    parser.add_argument('--cdp', type=str, default='http://localhost:9222',
                       help='Chrome DevTools Protocol URL')
    
    args = parser.parse_args()
    
    clicker = ElementClicker(args.cdp)
    asyncio.run(clicker.click_by_html_line(args.html_file, args.line_number, args.url))


if __name__ == "__main__":
    main()

