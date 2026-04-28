local heading_aliases = {
  ["参考文献(本章引用):"] = "参考文献",
  ["代码锚点索引(本章引用):"] = "代码锚点索引",
}

function Para(el)
  local text = pandoc.utils.stringify(el)
  local heading = heading_aliases[text]

  if heading then
    return pandoc.Header(4, heading)
  end
end
